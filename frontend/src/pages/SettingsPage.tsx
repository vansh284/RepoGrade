import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { BackupInfo } from "../api/client";

export default function SettingsPage() {
  const [backupPath, setBackupPath] = useState("");
  const [savedPath, setSavedPath] = useState("");
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const loadSettings = async () => {
    try {
      const setting = await api.settings.getBackupPath();
      setBackupPath(setting.value);
      setSavedPath(setting.value);
    } catch {
      // Not configured yet
    }
  };

  const loadBackups = async () => {
    try {
      const list = await api.backup.list();
      setBackups(list);
    } catch {
      // No backups yet
    }
  };

  useEffect(() => {
    loadSettings();
    loadBackups();
  }, []);

  const handleSavePath = async () => {
    if (!backupPath.trim()) return;
    setError("");
    setMessage("");
    try {
      const setting = await api.settings.setBackupPath(backupPath.trim());
      setSavedPath(setting.value);
      setMessage("Backup path saved.");
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleBackup = async () => {
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const result = await api.backup.create();
      setMessage(`Backup created: ${result.filename}`);
      loadBackups();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (filename: string) => {
    if (!confirm(`Restore database from ${filename}? This will replace the current database.`)) {
      return;
    }
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const result = await api.backup.restore(filename);
      setMessage(result.message);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <h2>Settings</h2>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 8 }}>
            dismiss
          </button>
        </div>
      )}

      {message && (
        <div style={{ color: "green", marginBottom: 16 }}>
          {message}
          <button onClick={() => setMessage("")} style={{ marginLeft: 8 }}>
            dismiss
          </button>
        </div>
      )}

      <h3>Backup Directory</h3>
      <div style={{ marginBottom: 16 }}>
        <input
          value={backupPath}
          onChange={(e) => setBackupPath(e.target.value)}
          placeholder="e.g. C:\backups\repograde"
          style={{ width: 400, marginRight: 8 }}
        />
        <button onClick={handleSavePath}>Save Path</button>
      </div>

      {savedPath && (
        <div style={{ marginBottom: 24 }}>
          <button onClick={handleBackup} disabled={loading}>
            {loading ? "Working..." : "Backup Now"}
          </button>
        </div>
      )}

      <h3>Available Backups</h3>
      {backups.length === 0 ? (
        <p>No backups found.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Filename</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 8 }}>Created</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #ccc", padding: 8 }}>Size</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #ccc", padding: 8 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {backups.map((b) => (
              <tr key={b.filename}>
                <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{b.filename}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                  {new Date(b.created_at).toLocaleString()}
                </td>
                <td style={{ padding: 8, borderBottom: "1px solid #eee", textAlign: "right" }}>
                  {formatSize(b.size_bytes)}
                </td>
                <td style={{ padding: 8, borderBottom: "1px solid #eee", textAlign: "right" }}>
                  <button onClick={() => handleRestore(b.filename)} disabled={loading}>
                    Restore
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
