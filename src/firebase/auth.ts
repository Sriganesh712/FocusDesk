import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  type User,
} from 'firebase/auth';
import { auth, isFirebaseConfigured } from './config';

export interface AuthState {
  user: User | null;
  localOwnerId: string;
  loading: boolean;
  isCloudAuth: boolean;
}

// Default stable local device owner ID if unauthenticated or offline
const LOCAL_FALLBACK_OWNER_ID = 'local-owner-focusdesk';

export function getLocalOwnerId(): string {
  let id = localStorage.getItem('focusdesk_local_owner_id');
  if (!id) {
    id = LOCAL_FALLBACK_OWNER_ID;
    localStorage.setItem('focusdesk_local_owner_id', id);
  }
  return id;
}

export function subscribeToAuth(callback: (state: AuthState) => void): () => void {
  if (!isFirebaseConfigured || !auth) {
    callback({
      user: null,
      localOwnerId: getLocalOwnerId(),
      loading: false,
      isCloudAuth: false,
    });
    return () => {};
  }

  return onAuthStateChanged(auth, (user) => {
    callback({
      user,
      localOwnerId: user ? user.uid : getLocalOwnerId(),
      loading: false,
      isCloudAuth: true,
    });
  });
}

export async function loginWithEmail(email: string, pass: string): Promise<User> {
  if (!auth) throw new Error('Firebase authentication is not configured');
  const cred = await signInWithEmailAndPassword(auth, email, pass);
  return cred.user;
}

export async function registerWithEmail(email: string, pass: string): Promise<User> {
  if (!auth) throw new Error('Firebase authentication is not configured');
  const cred = await createUserWithEmailAndPassword(auth, email, pass);
  return cred.user;
}

export async function logout(): Promise<void> {
  if (!auth) return;
  await firebaseSignOut(auth);
}
