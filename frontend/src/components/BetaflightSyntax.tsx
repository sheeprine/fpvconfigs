import { Fragment } from 'react'

// Very small hand-rolled highlighter for Betaflight CLI dump files.
// Not a general grammar — just enough structure to make the three
// recurring shapes (comments, `set key = value`, bare commands) scannable.

const NUMBER_RE = /^-?\d+(\.\d+)?$/

function highlightValue(value: string, key: string) {
  return (
    <Fragment>
      <span className="text-sky-400">{key}</span>
      <span className="text-slate-500"> = </span>
      <span className={NUMBER_RE.test(value.trim()) ? 'text-cyan-300' : 'text-amber-300'}>
        {value}
      </span>
    </Fragment>
  )
}

function highlightTokens(tokens: string[]) {
  return tokens.map((token, i) => (
    <Fragment key={i}>
      {i > 0 && ' '}
      <span className={NUMBER_RE.test(token) ? 'text-cyan-300' : 'text-slate-200'}>{token}</span>
    </Fragment>
  ))
}

function highlightLine(line: string) {
  const trimmed = line.trim()

  if (trimmed === '') {
    return null
  }

  if (trimmed.startsWith('#')) {
    return <span className="text-slate-500 italic">{line}</span>
  }

  const setMatch = trimmed.match(/^(set)\s+(\S+)\s*=\s*(.*)$/)
  if (setMatch) {
    const [, setKeyword, key, value] = setMatch
    const leadingWs = line.slice(0, line.length - line.trimStart().length)
    return (
      <Fragment>
        {leadingWs}
        <span className="text-orange-400 font-semibold">{setKeyword}</span>{' '}
        {highlightValue(value, key)}
      </Fragment>
    )
  }

  const [command, ...rest] = trimmed.split(/(\s+)/).filter((t) => t !== '')
  const leadingWs = line.slice(0, line.length - line.trimStart().length)
  return (
    <Fragment>
      {leadingWs}
      <span className="text-orange-400 font-semibold">{command}</span>
      {rest.length > 0 && ' '}
      {highlightTokens(rest.join('').split(' ').filter((t) => t !== ''))}
    </Fragment>
  )
}

interface BetaflightSyntaxProps {
  content: string
}

export default function BetaflightSyntax({ content }: BetaflightSyntaxProps) {
  const lines = content.split('\n')
  return (
    <pre className="font-mono text-sm leading-relaxed whitespace-pre overflow-x-auto">
      {lines.map((line, i) => (
        <div key={i} className="px-4 hover:bg-slate-700/20">
          <span className="inline-block w-10 mr-2 text-right text-slate-600 select-none">
            {i + 1}
          </span>
          {highlightLine(line) ?? ' '}
        </div>
      ))}
    </pre>
  )
}
