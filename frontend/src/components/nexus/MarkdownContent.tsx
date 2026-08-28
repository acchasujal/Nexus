import React from 'react'

interface MarkdownContentProps {
  content: string
  className?: string
}

type Block =
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'code'; language?: string; code: string }
  | { type: 'heading'; level: number; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'p'; text: string }

function isTableSeparator(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed.includes('-')) return false
  const cells = splitTableRow(trimmed)
  if (cells.length === 0) return false
  return cells.every((c) => /^:?-+:?$/.test(c.trim()))
}

function splitTableRow(line: string): string[] {
  let cleaned = line.trim()
  if (cleaned.startsWith('|')) cleaned = cleaned.slice(1)
  if (cleaned.endsWith('|')) cleaned = cleaned.slice(0, -1)
  return cleaned.split('|').map((cell) => cell.trim())
}

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.split('\n')
  const blocks: Block[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    // 1. Empty lines
    if (!trimmed) {
      i++
      continue
    }

    // 2. Code blocks (```)
    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim()
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      if (i < lines.length && lines[i].trim().startsWith('```')) {
        i++
      }
      blocks.push({
        type: 'code',
        language,
        code: codeLines.join('\n'),
      })
      continue
    }

    // 3. Tables
    // A table must have a header line with '|' and the NEXT line must be a separator line
    if (trimmed.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headers = splitTableRow(trimmed)
      i += 2 // skip header and separator

      const rows: string[][] = []
      while (i < lines.length) {
        const nextLine = lines[i].trim()
        if (!nextLine || !nextLine.includes('|')) {
          break
        }
        rows.push(splitTableRow(nextLine))
        i++
      }

      blocks.push({
        type: 'table',
        headers,
        rows,
      })
      continue
    }

    // 4. Headings (#, ##, ###, ####)
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/)
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2],
      })
      i++
      continue
    }

    // 5. Unordered lists (- , * , • )
    if (/^[-*•]\s+/.test(trimmed)) {
      const items: string[] = []
      while (i < lines.length) {
        const itemLine = lines[i].trim()
        const match = itemLine.match(/^[-*•]\s+(.+)$/)
        if (match) {
          items.push(match[1])
          i++
        } else if (itemLine && items.length > 0 && !itemLine.startsWith('#') && !itemLine.includes('|')) {
          // Continuation line of previous list item
          items[items.length - 1] += ` ${itemLine}`
          i++
        } else {
          break
        }
      }
      blocks.push({ type: 'ul', items })
      continue
    }

    // 6. Ordered lists (1. , 2. )
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = []
      while (i < lines.length) {
        const itemLine = lines[i].trim()
        const match = itemLine.match(/^\d+\.\s+(.+)$/)
        if (match) {
          items.push(match[1])
          i++
        } else if (itemLine && items.length > 0 && !itemLine.startsWith('#') && !itemLine.includes('|')) {
          items[items.length - 1] += ` ${itemLine}`
          i++
        } else {
          break
        }
      }
      blocks.push({ type: 'ol', items })
      continue
    }

    // 7. Regular paragraph text (group contiguous non-empty lines)
    const pLines: string[] = [line]
    i++
    while (i < lines.length) {
      const nextLine = lines[i]
      const nextTrimmed = nextLine.trim()
      if (
        !nextTrimmed ||
        nextTrimmed.startsWith('```') ||
        nextTrimmed.startsWith('#') ||
        /^[-*•]\s+/.test(nextTrimmed) ||
        /^\d+\.\s+/.test(nextTrimmed) ||
        (nextTrimmed.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
      ) {
        break
      }
      pLines.push(nextLine)
      i++
    }
    blocks.push({
      type: 'p',
      text: pLines.join('\n'),
    })
  }

  return blocks
}

function renderInline(text: string): React.ReactNode {
  // Regex to split by inline code, bold, italic, and links
  const tokens: React.ReactNode[] = []
  let remaining = text
  let keyIdx = 0

  while (remaining) {
    // 1. Inline code: `code`
    const codeMatch = remaining.match(/^`([^`]+)`/)
    if (codeMatch) {
      tokens.push(
        <code
          key={keyIdx++}
          className="rounded bg-neutral-100 px-1 py-0.5 font-mono text-[11px] text-neutral-900 border border-neutral-200"
        >
          {codeMatch[1]}
        </code>
      )
      remaining = remaining.slice(codeMatch[0].length)
      continue
    }

    // 2. Bold: **text** or __text__
    const boldMatch = remaining.match(/^(\*\*|__)(.+?)\1/)
    if (boldMatch) {
      tokens.push(
        <strong key={keyIdx++} className="font-semibold text-neutral-900">
          {renderInline(boldMatch[2])}
        </strong>
      )
      remaining = remaining.slice(boldMatch[0].length)
      continue
    }

    // 3. Italic: *text* or _text_
    const italicMatch = remaining.match(/^(\*|_)(.+?)\1/)
    if (italicMatch) {
      tokens.push(
        <em key={keyIdx++} className="italic text-neutral-800">
          {renderInline(italicMatch[2])}
        </em>
      )
      remaining = remaining.slice(italicMatch[0].length)
      continue
    }

    // 4. Markdown links: [label](url)
    const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/)
    if (linkMatch) {
      tokens.push(
        <a
          key={keyIdx++}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-blue-600 hover:text-blue-800 hover:underline"
        >
          {linkMatch[1]}
        </a>
      )
      remaining = remaining.slice(linkMatch[0].length)
      continue
    }

    // 5. Plain text segment up to the next special character
    const nextSpecial = remaining.search(/[`*_\[]/)
    if (nextSpecial === -1) {
      tokens.push(remaining)
      break
    } else if (nextSpecial === 0) {
      // First character is special but didn't match any syntax -> treat as literal char
      tokens.push(remaining[0])
      remaining = remaining.slice(1)
    } else {
      tokens.push(remaining.slice(0, nextSpecial))
      remaining = remaining.slice(nextSpecial)
    }
  }

  return <>{tokens}</>
}

export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  if (!content) return null

  const blocks = parseBlocks(content)

  return (
    <div className={`space-y-2 text-sm leading-relaxed text-neutral-900 ${className}`}>
      {blocks.map((block, bIdx) => {
        switch (block.type) {
          case 'table':
            return (
              <div
                key={bIdx}
                className="overflow-x-auto my-3 rounded-xl border border-neutral-200 bg-white shadow-2xs"
              >
                <table className="min-w-full text-left text-xs divide-y divide-neutral-200">
                  <thead className="bg-neutral-50/90 text-neutral-800 font-semibold text-[11px] uppercase tracking-wider">
                    <tr>
                      {block.headers.map((h, hIdx) => (
                        <th
                          key={hIdx}
                          className="px-3.5 py-2.5 border-r last:border-r-0 border-neutral-200 whitespace-nowrap"
                        >
                          {renderInline(h)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100 bg-white">
                    {block.rows.map((row, rIdx) => (
                      <tr
                        key={rIdx}
                        className={rIdx % 2 === 1 ? 'bg-neutral-50/40 hover:bg-neutral-100/50' : 'hover:bg-neutral-50/60'}
                      >
                        {row.map((cell, cIdx) => (
                          <td
                            key={cIdx}
                            className="px-3.5 py-2 border-r last:border-r-0 border-neutral-200 text-neutral-800"
                          >
                            {renderInline(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )

          case 'heading': {
            const HeadingTag = `h${Math.min(block.level + 2, 6)}` as React.ElementType
            const headingClasses =
              block.level === 1
                ? 'text-base font-bold text-neutral-900 pt-2 pb-1 border-b border-neutral-200'
                : block.level === 2
                ? 'text-sm font-bold text-neutral-900 pt-2 pb-0.5'
                : 'text-xs font-bold uppercase tracking-wider text-neutral-800 pt-1.5'
            return (
              <HeadingTag key={bIdx} className={headingClasses}>
                {renderInline(block.text)}
              </HeadingTag>
            )
          }

          case 'ul':
            return (
              <ul key={bIdx} className="list-disc list-inside space-y-1 pl-1 text-sm text-neutral-800 my-1.5">
                {block.items.map((item, iIdx) => (
                  <li key={iIdx} className="leading-relaxed">
                    {renderInline(item)}
                  </li>
                ))}
              </ul>
            )

          case 'ol':
            return (
              <ol key={bIdx} className="list-decimal list-inside space-y-1 pl-1 text-sm text-neutral-800 my-1.5">
                {block.items.map((item, iIdx) => (
                  <li key={iIdx} className="leading-relaxed">
                    {renderInline(item)}
                  </li>
                ))}
              </ol>
            )

          case 'code':
            return (
              <div key={bIdx} className="my-2 rounded-lg bg-neutral-900 p-3 text-xs font-mono text-neutral-100 overflow-x-auto shadow-xs">
                {block.language && (
                  <div className="text-[10px] text-neutral-400 font-sans uppercase mb-1">{block.language}</div>
                )}
                <pre className="whitespace-pre">{block.code}</pre>
              </div>
            )

          case 'p':
            return (
              <p key={bIdx} className="text-sm leading-relaxed whitespace-pre-wrap">
                {renderInline(block.text)}
              </p>
            )

          default:
            return null
        }
      })}
    </div>
  )
}
