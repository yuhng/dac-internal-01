export const SPELLING: Record<string, string> = {
  experiance: 'experience', managment: 'management', recieve: 'receive', recieved: 'received',
  sucessfully: 'successfully', succesfully: 'successfully', acheived: 'achieved', acheive: 'achieve',
  developped: 'developed', enviroment: 'environment', seperate: 'separate', occured: 'occurred',
  commited: 'committed', teh: 'the', definately: 'definitely', accross: 'across', begining: 'beginning',
}

const PAST_TENSE: Record<string, string> = {
  creating: 'created', managing: 'managed', developing: 'developed', building: 'built',
  leading: 'led', maintaining: 'maintained', preparing: 'prepared', designing: 'designed',
}

export const WEAK_PHRASES: [RegExp, (match: string, verb?: string) => string, string][] = [
  [/\bresponsible for (creating|managing|developing|building|leading|maintaining|preparing|designing)\b/gi, (_, verb) => PAST_TENSE[verb!.toLowerCase()], '“Responsible for…” → action verb'],
  [/\bresponsible for\b/gi, () => 'owned', '“Responsible for” → “Owned”'],
  [/\bworked on\b/gi, () => 'delivered', '“Worked on” → “Delivered”'],
  [/\bhelped with\b/gi, () => 'supported', '“Helped with” → “Supported”'],
  [/\b(was|were) involved in\b/gi, () => 'contributed to', '“Was involved in” → “Contributed to”'],
  [/\bin charge of\b/gi, () => 'led', '“In charge of” → “Led”'],
]
