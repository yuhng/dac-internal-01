export const countWords = (text: string) => (text.trim().match(/\S+/g) ?? []).length

export const listJoin = (items: string[]) =>
  items.length < 2
    ? items.join('')
    : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`
