import { Monitor, Bell, ShieldCheck } from 'lucide-react'

/**
 * Settings page — currently a structured placeholder.
 * Settings configuration requires a user profile endpoint from the backend.
 * Each section has been stubbed with the fields it will eventually manage.
 */
export default function Settings() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-h1 font-bold text-neutral-900">Settings</h1>
        <p className="text-body text-neutral-500">
          Application preferences and account configuration
        </p>
      </div>

      {/* Display Settings */}
      <section aria-labelledby="display-settings-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Monitor className="h-5 w-5 text-neutral-500" aria-hidden="true" />
          <h2 id="display-settings-heading" className="text-h2 font-semibold text-neutral-900">
            Display
          </h2>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-neutral-200">
            <div>
              <p className="text-small font-semibold text-neutral-800">Table Density</p>
              <p className="text-caption text-neutral-500">Adjustable via the Dense / Comfortable toggle in the header</p>
            </div>
            <span className="text-caption text-neutral-400 italic">Header control</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-small font-semibold text-neutral-800">Language / Locale</p>
              <p className="text-caption text-neutral-500">Language follows the browser locale</p>
            </div>
            <span className="text-caption text-neutral-400 italic">Browser default</span>
          </div>
        </div>
      </section>

      {/* Notification Preferences */}
      <section aria-labelledby="notifications-settings-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Bell className="h-5 w-5 text-neutral-500" aria-hidden="true" />
          <h2 id="notifications-settings-heading" className="text-h2 font-semibold text-neutral-900">
            Notifications
          </h2>
        </div>
        <div className="py-3 border border-dashed border-neutral-300 rounded-radius-sm bg-neutral-100 text-center p-4">
          <p className="text-small font-semibold text-neutral-600">Notification preferences unavailable</p>
          <p className="text-caption text-neutral-400 mt-1">
            Requires push notification service integration (backend Lane 3)
          </p>
        </div>
      </section>

      {/* Security */}
      <section aria-labelledby="security-settings-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <ShieldCheck className="h-5 w-5 text-neutral-500" aria-hidden="true" />
          <h2 id="security-settings-heading" className="text-h2 font-semibold text-neutral-900">
            Security &amp; Access
          </h2>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-neutral-200">
            <div>
              <p className="text-small font-semibold text-neutral-800">Active Role</p>
              <p className="text-caption text-neutral-500">Role is assigned at login via the authentication provider</p>
            </div>
            <span className="text-caption text-neutral-400 italic">View-only</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="text-small font-semibold text-neutral-800">Session Management</p>
              <p className="text-caption text-neutral-500">Session controls are managed by the authentication provider</p>
            </div>
            <span className="text-caption text-neutral-400 italic">Provider managed</span>
          </div>
        </div>
      </section>
    </div>
  )
}
