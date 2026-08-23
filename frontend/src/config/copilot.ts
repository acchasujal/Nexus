export type CopilotProvider = 'convokraft' | 'quickml'

const configuredProvider = import.meta.env.VITE_COPILOT_PROVIDER?.toLowerCase()

export const COPILOT_PROVIDER: CopilotProvider = configuredProvider === 'quickml'
  ? 'quickml'
  : 'convokraft'

export const CONVOKRAFT_CONFIG = {
  botName: import.meta.env.VITE_CONVOKRAFT_BOT_NAME || 'voiceassistant',
  projectId: import.meta.env.VITE_CONVOKRAFT_PROJECT_ID || '51441000000017001',
  orgId: import.meta.env.VITE_CONVOKRAFT_ORG_ID || '60077090566',
  sdkUrl: 'https://console.catalyst.zoho.in/convokraft/assets/js/convokraft-chat-sdk.js',
} as const
