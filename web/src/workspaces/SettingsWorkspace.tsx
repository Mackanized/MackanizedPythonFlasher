import React, { useEffect, useState } from 'react';
import { Check, FolderOpen } from 'lucide-react';
import { WorkstationSettingsPayload, getPyWebViewGateway } from '../services/pywebview/bridge';
import { applyDesktopPreferences } from '../services/theme/preferences';

type SettingsKey = keyof WorkstationSettingsPayload;

export default function SettingsWorkspace() {
  const gateway = getPyWebViewGateway();
  const [settings, setSettings] = useState<WorkstationSettingsPayload>({
    theme: 'dark',
    densityMode: 'standard',
    defaultAdapter: 'mock',
    j2534Dll: '',
    baudrate: 500000,
    disablePreflight: true,
  });
  const [loading, setLoading] = useState(true);
  const [savedNotice, setSavedNotice] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchSettings = async () => {
      try {
        const loaded = await gateway.getSettings();
        if (mounted && loaded) {
          setSettings((prev) => {
            const next = { ...prev, ...loaded };
            applyDesktopPreferences(next);
            return next;
          });
        }
      } catch (err) {
        console.warn('Failed to load settings:', err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    void fetchSettings();
    return () => {
      mounted = false;
    };
  }, [gateway]);

  const handleChange = <K extends SettingsKey>(key: K, value: WorkstationSettingsPayload[K]) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: value };
      if (key === 'theme' || key === 'densityMode') {
        applyDesktopPreferences(next);
      }
      return next;
    });
    setSavedNotice('');
  };

  const handleSave = async () => {
    setSaving(true);
    setSavedNotice('');
    try {
      const ok = await gateway.updateSettings(settings);
      if (ok) {
        setSavedNotice('Workstation preferences saved successfully.');
      } else {
        setSavedNotice('Failed to persist settings.');
      }
    } catch (err) {
      setSavedNotice(`Error saving settings: ${err}`);
    } finally {
      setSaving(false);
    }
  };

  const handleBrowseDll = async () => {
    try {
      const result = await gateway.selectCalibrationFile('dll');
      if (result && result.path) {
        handleChange('j2534Dll', result.path);
      }
    } catch (err) {
      console.warn('DLL file selection error:', err);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-xs text-slate-400 font-sans">
        Loading workstation settings...
      </div>
    );
  }

  return (
    <div
      className="space-y-6 overflow-y-auto h-full max-w-4xl select-none font-sans text-xs"
      style={{
        padding: 'var(--workspace-padding)',
        backgroundColor: 'var(--bg-surface-base)',
        color: 'var(--text-primary)',
      }}
    >
      <div className="py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--panel-border)' }}>
        <div>
          <div>
            <h1 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>Workstation and hardware settings</h1>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Configure CAN adapters, J2534 DLL paths, bus baud rates, and workstation layout.</p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="h-8 px-4 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-semibold rounded-sm transition-colors flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
        >
          <Check className="w-3.5 h-3.5" />
          <span>{saving ? 'Saving...' : 'Save preferences'}</span>
        </button>
      </div>

      {savedNotice && (
        <div className="p-3 bg-[#1B2C24] border border-[#10B981]/30 rounded-sm text-emerald-300 font-medium">
          {savedNotice}
        </div>
      )}

      <div className="space-y-6">
        <div className="p-5 rounded-sm border space-y-4" style={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)' }}>
          <h2 className="text-sm font-bold border-b pb-2" style={{ color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}>
            Hardware adapter and PassThru settings
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-primary)' }}>
                Default hardware adapter
              </label>
              <select
                value={settings.defaultAdapter}
                onChange={(e) => handleChange('defaultAdapter', e.target.value)}
                className="w-full px-3 text-xs rounded-sm border focus:border-[#3B82F6]"
                style={{ height: 'var(--control-height)', backgroundColor: 'var(--control-bg)', color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}
              >
                <option value="mock">Mock Adapter (Offline Simulator)</option>
                <option value="j2534">SAE J2534 PassThru (DLL)</option>
                <option value="kvaser">Kvaser CANlib (Native USB)</option>
                <option value="socketcan">Linux SocketCAN (Native Kernel)</option>
              </select>
              <span className="text-[11px] mt-1 block" style={{ color: 'var(--text-muted)' }}>
                Primary adapter interface loaded on workstation boot.
              </span>
            </div>

            <div>
              <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-primary)' }}>
                Default CAN bus bit rate
              </label>
              <select
                value={settings.baudrate}
                onChange={(e) => handleChange('baudrate', Number(e.target.value))}
                className="w-full px-3 text-xs rounded-sm border focus:border-[#3B82F6]"
                style={{ height: 'var(--control-height)', backgroundColor: 'var(--control-bg)', color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}
              >
                <option value={500000}>500 kbps (Standard High-Speed CAN)</option>
                <option value={250000}>250 kbps (Medium-Speed CAN)</option>
                <option value={33333}>33.3 kbps (GMLAN Low-Speed SW-CAN)</option>
              </select>
              <span className="text-[11px] mt-1 block" style={{ color: 'var(--text-muted)' }}>
                Bus speed initialized during adapter channel open.
              </span>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-primary)' }}>
              Custom J2534 vendor DLL path override
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={settings.j2534Dll}
                onChange={(e) => handleChange('j2534Dll', e.target.value)}
                placeholder="Auto-detect J2534 DLL from system registry (e.g. C:\Program Files\PassThru\...)"
                className="flex-1 px-3 text-xs rounded-sm border focus:border-[#3B82F6] font-mono-code"
                style={{ height: 'var(--control-height)', backgroundColor: 'var(--control-bg)', color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}
              />
              <button
                type="button"
                onClick={handleBrowseDll}
                className="h-9 px-3 bg-[#2A2D38] hover:bg-[#323644] text-[#E2E8F0] rounded-sm border border-[#333646] font-semibold flex items-center space-x-1.5"
              >
                <FolderOpen className="w-3.5 h-3.5" />
                <span>Browse...</span>
              </button>
            </div>
            <span className="text-[11px] mt-1 block" style={{ color: 'var(--text-muted)' }}>
              Leave blank to automatically enumerate registered J2534 PassThru drivers from Windows Registry.
            </span>
          </div>
        </div>

        <div className="p-5 rounded-sm border space-y-4" style={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)' }}>
          <h2 className="text-sm font-bold border-b pb-2" style={{ color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}>
            Theme and visual density preferences
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-primary)' }}>
                Workstation theme preset
              </label>
              <select
                value={settings.theme}
                onChange={(e) => handleChange('theme', e.target.value)}
                className="w-full px-3 text-xs rounded-sm border focus:border-[#3B82F6]"
                style={{ height: 'var(--control-height)', backgroundColor: 'var(--control-bg)', color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}
              >
                <option value="dark">Dark Charcoal (Default Engineering Palette)</option>
                <option value="oled">Workshop OLED (High Contrast Pitch Black)</option>
                <option value="light">Technical Light (Clean Workshop Light)</option>
              </select>
              <span className="text-[11px] mt-1 block" style={{ color: 'var(--text-muted)' }}>
                Visual presentation tokens enforced across all workspaces.
              </span>
            </div>

            <div>
              <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-primary)' }}>
                Layout density mode
              </label>
              <select
                value={settings.densityMode}
                onChange={(e) => handleChange('densityMode', e.target.value)}
                className="w-full px-3 text-xs rounded-sm border focus:border-[#3B82F6]"
                style={{ height: 'var(--control-height)', backgroundColor: 'var(--control-bg)', color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}
              >
                <option value="standard">Standard Engineering</option>
                <option value="compact">Compact High-Density</option>
              </select>
              <span className="text-[11px] mt-1 block" style={{ color: 'var(--text-muted)' }}>
                Controls row height and vertical rhythm across hex view and tables.
              </span>
            </div>
          </div>
        </div>

        <div className="p-5 rounded-sm border space-y-4" style={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)' }}>
          <h2 className="text-sm font-bold border-b pb-2" style={{ color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}>
            Preflight safety validation controls
          </h2>

          <div className="flex items-start space-x-3 p-3 border rounded-sm" style={{ backgroundColor: 'var(--control-bg)', borderColor: 'var(--panel-border)' }}>
            <input
              type="checkbox"
              id="disablePreflight"
              checked={settings.disablePreflight}
              onChange={(e) => handleChange('disablePreflight', e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-[#2A2D38] bg-[#1B1C22] text-[#3B82F6] focus:ring-0 cursor-pointer"
            />
            <label htmlFor="disablePreflight" className="cursor-pointer space-y-1">
              <span className="text-xs font-semibold text-[#E2E8F0] block">
                Disable Preflight Safety Checks (Off by default for direct binary flashing)
              </span>
              <span className="text-[11px] text-slate-400 block leading-relaxed">
                When enabled, preflight file size, checksum, and region boundary checks are bypassed, allowing any calibration or full firmware binary file to be flashed directly to the target ECU without pre-write rejection.
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
