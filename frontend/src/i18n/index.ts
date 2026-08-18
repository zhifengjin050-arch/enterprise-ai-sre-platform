import zh, { type Dict } from './zh'
import en from './en'

export type Locale = 'zh' | 'en'
export type { Dict }

export const dictionaries: Record<Locale, Dict> = { zh, en }

type Path<T, Prefix extends string = ''> = T extends object
  ? {
      [K in keyof T & string]: T[K] extends object
        ? Path<T[K], Prefix extends '' ? K : `${Prefix}.${K}`>
        : Prefix extends ''
          ? K
          : `${Prefix}.${K}`
    }[keyof T & string]
  : never

export type MessageKey = Path<Dict>

export function lookup(dict: Dict, key: string): string {
  const parts = key.split('.')
  let cur: unknown = dict
  for (const p of parts) {
    if (cur && typeof cur === 'object' && p in (cur as object)) {
      cur = (cur as Record<string, unknown>)[p]
    } else {
      return key
    }
  }
  return typeof cur === 'string' ? cur : key
}
