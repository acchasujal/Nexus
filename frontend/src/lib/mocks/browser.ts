import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'
import { nexusHandlers } from './nexusHandlers'

export const worker = setupWorker(...handlers, ...nexusHandlers)
