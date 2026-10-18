import React, { useState } from 'react';
import {
  X,
  LogIn,
  UserPlus,
  Cloud,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react';
import { loginWithEmail, registerWithEmail } from '../firebase/auth';
import { isFirebaseConfigured } from '../firebase/config';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        await registerWithEmail(email, password);
      } else {
        await loginWithEmail(email, password);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-auth card-glass" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="flex items-center gap-2">
            <Cloud size={20} className="text-primary" />
            <h2>{isRegister ? 'Create Cloud Account' : 'Sign In to Cloud'}</h2>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {!isFirebaseConfigured ? (
          <div className="p-4 text-center">
            <ShieldCheck size={40} className="text-primary mx-auto mb-2" />
            <h3>Local-First Mode Active</h3>
            <p className="text-muted text-sm mt-2">
              FocusDesk is running in standalone local mode. All tasks are securely saved to your browser's IndexedDB.
            </p>
            <div className="bg-base border rounded p-3 text-xs text-left text-muted mt-4">
              <strong>To enable cloud sync:</strong>
              <p className="mt-1">
                Add your Firebase project keys to <code>.env</code> based on <code>.env.example</code>.
              </p>
            </div>
            <button className="btn-secondary w-full mt-4" onClick={onClose}>
              Continue Local
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="modal-form">
            <p className="text-muted text-sm mb-4">
              Sync tasks seamlessly across your browser and the STM32 touchscreen kiosk.
            </p>

            {error && (
              <div className="p-3 mb-3 text-danger text-sm bg-danger-bg border border-danger rounded flex items-center gap-2">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                required
                placeholder="developer@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="form-input"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                required
                placeholder="••••••••"
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="form-input"
              />
            </div>

            <button type="submit" className="btn-primary w-full mt-2" disabled={loading}>
              {loading ? (
                <span>Authenticating...</span>
              ) : isRegister ? (
                <>
                  <UserPlus size={16} />
                  <span>Register Account</span>
                </>
              ) : (
                <>
                  <LogIn size={16} />
                  <span>Sign In</span>
                </>
              )}
            </button>

            <div className="text-center mt-4 text-sm text-muted">
              {isRegister ? (
                <span>
                  Already have an account?{' '}
                  <button
                    type="button"
                    className="text-primary underline bg-transparent border-0"
                    onClick={() => {
                      setIsRegister(false);
                      setError(null);
                    }}
                  >
                    Sign In
                  </button>
                </span>
              ) : (
                <span>
                  Need an account?{' '}
                  <button
                    type="button"
                    className="text-primary underline bg-transparent border-0"
                    onClick={() => {
                      setIsRegister(true);
                      setError(null);
                    }}
                  >
                    Create one
                  </button>
                </span>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
