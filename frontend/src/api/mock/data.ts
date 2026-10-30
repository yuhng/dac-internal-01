/** Each entry is a display name followed by the terms that count as a match. */
export const SKILLS: string[][] = [
  ['SQL', 'sql'], ['Excel', 'excel', 'spreadsheets'], ['Python', 'python'], ['pandas', 'pandas'], ['Tableau', 'tableau'],
  ['Power BI', 'power bi'], ['Looker', 'looker'], ['Statistics', 'statistics', 'statistical'],
  ['A/B testing', 'a/b testing', 'a/b test', 'ab testing', 'experimentation'], ['ETL', 'etl', 'data pipelines'],
  ['BigQuery', 'bigquery'], ['Snowflake', 'snowflake'], ['Data warehouse', 'data warehouse', 'data warehouses'],
  ['Data visualization', 'data visualization', 'data visualisation'], ['Dashboards', 'dashboard', 'dashboards'],
  ['Machine learning', 'machine learning'], ['Communication', 'communication'],
  ['Stakeholder management', 'stakeholder management', 'stakeholders'],
  ['React', 'react'], ['TypeScript', 'typescript'], ['JavaScript', 'javascript'], ['HTML', 'html'], ['CSS', 'css'],
  ['Accessibility', 'accessibility', 'accessible', 'wcag', 'a11y'], ['REST APIs', 'rest api', 'rest apis', 'restful'],
  ['Jest', 'jest'], ['Unit testing', 'unit testing', 'unit tests', 'automated testing'], ['Git', 'git'],
  ['CI/CD', 'ci/cd', 'continuous integration'], ['Web performance', 'web performance', 'core web vitals', 'page load speed', 'performance optimization'],
  ['Design systems', 'design system', 'design systems'], ['Figma', 'figma'], ['Agile', 'agile', 'scrum'],
  ['Node.js', 'node.js', 'nodejs'], ['AWS', 'aws'], ['Docker', 'docker'], ['Project management', 'project management'],
  ['Leadership', 'leadership'], ['Java', 'java'], ['Spark', 'spark'], ['Salesforce', 'salesforce'], ['SEO', 'seo'],
]

export const STOP_WORDS = new Set(
  'a an the and or of to in for on with at by from as is are be been was were will you your we our us they their this that these those it its into over per can may must should have has had not but if than then so such who what which when where how all any each more most other some own same very also about using use used work working role team join years year plus strong excellent experience ability skills skill including within across etc'.split(' '),
)

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
