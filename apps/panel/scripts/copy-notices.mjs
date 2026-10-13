import { cpSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const root = new URL('../../../', import.meta.url)
const output = new URL('../dist/', import.meta.url)
cpSync(fileURLToPath(new URL('licenses/', root)), fileURLToPath(new URL('licenses/', output)), { recursive: true })
cpSync(fileURLToPath(new URL('THIRD_PARTY_NOTICES.md', root)), fileURLToPath(new URL('THIRD_PARTY_NOTICES.md', output)))
