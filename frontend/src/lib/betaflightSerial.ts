// Reads a Betaflight CLI "diff all" backup directly from a flight controller
// connected over USB, via the Chromium-only Web Serial API.

const BAUD_RATE = 115200
const CLI_ENTER_DELAY_MS = 400
const BANNER_IDLE_MS = 300
const BANNER_TIMEOUT_MS = 2000
const DUMP_IDLE_MS = 1200
const DUMP_TIMEOUT_MS = 20000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function isSerialSupported(): boolean {
  return typeof navigator !== 'undefined' && 'serial' in navigator && !!navigator.serial
}

/**
 * Reads from `reader` until no new data has arrived for `idleMs`, or
 * `timeoutMs` total has elapsed. Betaflight's CLI has no explicit
 * end-of-response marker, so idle-based capture is the practical option.
 */
type ReadOutcome =
  | { timedOut: false; value: string | undefined; done: boolean }
  | { timedOut: true }

async function readUntilIdle(
  reader: ReadableStreamDefaultReader<string>,
  idleMs: number,
  timeoutMs: number
): Promise<string> {
  let buffer = ''
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    const remaining = deadline - Date.now()
    const waitMs = Math.min(idleMs, Math.max(remaining, 0))

    const outcome: ReadOutcome = await Promise.race([
      reader.read().then(({ value, done }): ReadOutcome => ({ timedOut: false, value, done })),
      sleep(waitMs).then((): ReadOutcome => ({ timedOut: true })),
    ])

    if (outcome.timedOut) {
      if (buffer.length > 0) break
      continue
    }

    if (outcome.done) break
    if (outcome.value) buffer += outcome.value
  }

  return buffer
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

  if (!port.readable || !port.writable) {
    await port.close()
    throw new Error('Serial port has no readable/writable stream.')
  }

  const textEncoder = new TextEncoderStream()
  const writableClosed = textEncoder.readable.pipeTo(port.writable)
  const writer = textEncoder.writable.getWriter()

  const textDecoder = new TextDecoderStream()
  const readableClosed = port.readable.pipeTo(textDecoder.writable as WritableStream<Uint8Array>)
  const reader = textDecoder.readable.getReader()

  try {
    onStatus?.('Entering CLI mode…')
    await writer.write('#\n')
    await sleep(CLI_ENTER_DELAY_MS)
    // Drain the CLI banner/prompt so it doesn't get mixed into the dump.
    await readUntilIdle(reader, BANNER_IDLE_MS, BANNER_TIMEOUT_MS)

    onStatus?.('Reading configuration (diff all)…')
    await writer.write('diff all\n')
    const dump = await readUntilIdle(reader, DUMP_IDLE_MS, DUMP_TIMEOUT_MS)

    if (!dump.trim()) {
      throw new Error(
        'No data received from the flight controller. Check the connection and try again.'
      )
    }

    return dump
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
    await readableClosed.catch(() => {})

    await writer.close().catch(() => {})
    await writableClosed.catch(() => {})

    await port.close().catch(() => {})
  }
}
