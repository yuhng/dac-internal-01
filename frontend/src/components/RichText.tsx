import type { RichBlock } from '../api/types'

/** Renders **bold** spans. Everything else is plain text, so user input is never parsed as HTML. */
export function InlineText({ text }: { text: string }) {
  return text.split(/(\*\*[^*]+\*\*)/).map((part, i) =>
    /^\*\*[^*]+\*\*$/.test(part) ? <b key={i}>{part.slice(2, -2)}</b> : part,
  )
}

export function RichBlocks({ blocks }: { blocks: RichBlock[] }) {
  return (
    <div className="space-y-1.5">
      {blocks.map((block, i) => {
        if (block.kind === 'text') return <p key={i}><InlineText text={block.text} /></p>
        if (block.kind === 'quote') return <p key={i} className="italic"><InlineText text={block.text} /></p>
        const List = block.ordered ? 'ol' : 'ul'
        return (
          <List key={i} className={`pl-[18px] ${block.ordered ? 'list-decimal' : 'list-disc'}`}>
            {block.items.map((item, j) => <li key={j}><InlineText text={item} /></li>)}
          </List>
        )
      })}
    </div>
  )
}
