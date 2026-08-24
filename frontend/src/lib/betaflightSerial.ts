// Reads a Betaflight CLI "diff all" backup directly from a flight controller
// connected over USB, via the Chromium-only Web Serial API.

const BAUD_RATE = 115200
const CLI_ENTER_DELAY_MS = 500
const BANNER_IDLE_MS = 500
const BANNER_TIMEOUT_MS = 3000
const DUMP_IDLE_MS = 1200
const DUMP_TIMEOUT_MS = 20000
const MAX_DIFF_ALL_ATTEMPTS = 3

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function isSerialSupported(): boolean {
  return typeof navigator !== 'undefined' && 'serial' in navigator && !!navigator.serial
}

// Loose check that a captured dump actually contains the Betaflight version
// banner, used to decide whether a "diff all" attempt needs retrying (e.g.
// because it landed while the CLI was still printing its entry banner and
// got interleaved/corrupted).
function looksLikeBetaflightDump(text: string): boolean {
  return /#\s*Betaflight\s*\//i.test(text)
}

type ReadOutcome =
  | { timedOut: false; value: string | undefined; done: boolean }
  | { timedOut: true }

/**
 * Wraps a reader so idle-based capture never drops data. A naive
 * `Promise.race(reader.read(), timeout)` loses whatever chunk arrives after
 * the timeout wins a race, because the losing `read()` call is abandoned but
 * NOT cancelled — it stays queued on the reader and resolves later with real
 * data that nothing is listening for anymore. This keeps a single in-flight
 * `read()` alive across timeouts (and across separate `readUntilIdle` calls)
 * so no chunk is ever silently discarded.
 */
class IdleReader {
  private reader: ReadableStreamDefaultReader<string>
  private pending: Promise<ReadableStreamReadResult<string>> | null = null

  constructor(reader: ReadableStreamDefaultReader<string>) {
    this.reader = reader
  }

  private nextChunk(): Promise<ReadableStreamReadResult<string>> {
    if (!this.pending) {
      this.pending = this.reader.read()
    }
    return this.pending
  }

  /**
   * Reads until no new data has arrived for `idleMs`, or `timeoutMs` total
   * has elapsed. Betaflight's CLI has no explicit end-of-response marker,
   * so idle-based capture is the practical option.
   */
  async readUntilIdle(idleMs: number, timeoutMs: number): Promise<string> {
    let buffer = ''
    const deadline = Date.now() + timeoutMs

    while (Date.now() < deadline) {
      const remaining = deadline - Date.now()
      const waitMs = Math.min(idleMs, Math.max(remaining, 0))

      const outcome: ReadOutcome = await Promise.race([
        this.nextChunk().then(({ value, done }): ReadOutcome => ({ timedOut: false, value, done })),
        sleep(waitMs).then((): ReadOutcome => ({ timedOut: true })),
      ])

      if (outcome.timedOut) {
        if (buffer.length > 0) break
        continue
      }

      // This read has resolved for real: clear it so the next iteration (or
      // the next readUntilIdle call) starts a fresh one instead of re-racing
      // an already-consumed promise.
      this.pending = null
      if (outcome.done) break
      if (outcome.value) buffer += outcome.value
    }

    return buffer
  }

  async cancel(): Promise<void> {
    await this.reader.cancel().catch(() => {})
  }

  releaseLock(): void {
    this.reader.releaseLock()
  }
}

export async function readBetaflightConfig(
  onStatus?: (status: string) => void
): Promise<string> {
  if (!isSerialSupported()) {
    throw new Error(
      'Web Serial is not supported in this browser. Use a Chromium-based browser (Chrome or Edge) over HTTPS or localhost.'
    )
  }

  const port = await navigator.serial!.requestPort()
  await port.open({ baudRate: BAUD_RATE })

  // Many flight controllers' USB-CDC implementations only start streaming
  // once DTR is asserted (this is what Betaflight Configurator does too).
  await port.setSignals({ dataTerminalReady: true, requestToSend: true }).catch(() => {})

  if (!port.readable || !port.writable) {
    await port.close()
    throw new Error('Serial port has no readable/writable stream.')
  }

  const textEncoder = new TextEncoderStream()
  const writableClosed = textEncoder.readable.pipeTo(port.writable)
  const writer = textEncoder.writable.getWriter()

  const textDecoder = new TextDecoderStream()
  const readableClosed = port.readable.pipeTo(textDecoder.writable as WritableStream<Uint8Array>)
  const idleReader = new IdleReader(textDecoder.readable.getReader())

  try {
    onStatus?.('Entering CLI mode…')
    await writer.write('#\n')
    await sleep(CLI_ENTER_DELAY_MS)
    // Drain the CLI banner/prompt so it doesn't get mixed into the dump.
    // Any data that arrives right after this call's idle timeout naturally
    // carries over to the next readUntilIdle call via the shared IdleReader.
    await idleReader.readUntilIdle(BANNER_IDLE_MS, BANNER_TIMEOUT_MS)

    let dump = ''
    for (let attempt = 1; attempt <= MAX_DIFF_ALL_ATTEMPTS; attempt++) {
      onStatus?.(
        attempt === 1
          ? 'Reading configuration (diff all)…'
          : `Reading configuration (diff all)… retry ${attempt - 1}`
      )
      await writer.write('diff all\n')
      dump = await idleReader.readUntilIdle(DUMP_IDLE_MS, DUMP_TIMEOUT_MS)
      if (looksLikeBetaflightDump(dump)) break
      // The response may have landed while the CLI was still printing its
      // entry banner, corrupting the command. Give it a moment to settle
      // and try again rather than failing on the first noisy read.
      await sleep(500)
    }

    if (!dump.trim()) {
      throw new Error(
        'No data received from the flight controller. Check the connection and try again.'
      )
    }

    if (!looksLikeBetaflightDump(dump)) {
      const snippet = dump.trim().slice(0, 200)
      throw new Error(
        `Flight controller response did not look like a Betaflight CLI dump. Received: "${snippet}${dump.length > 200 ? '…' : ''}"`
      )
    }

    return dump
  } finally {
    await idleReader.cancel()
    idleReader.releaseLock()
    await readableClosed.catch(() => {})

    await writer.close().catch(() => {})
    await writableClosed.catch(() => {})

    await port.close().catch(() => {})
  }
}
