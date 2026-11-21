import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { AlertCircle, ArrowRight, Check, LoaderCircle, X } from 'lucide-react';
import { api } from './api';
import { initials, title } from './helpers';
import type { Auth, Settings } from './types';

type AppContextValue = { auth: Auth; setAuth: (auth: Auth) => void; settings: Settings; refreshSettings: () => void; toast: (message: string) => void };
export const AppContext = createContext<AppContextValue>(null!);
export const useApp = () => useContext(AppContext);

export function useResource<T>(path: string, enabled = true) {
  const [data, setData] = useState<T | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(enabled), [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!enabled) { setLoading(false); return; }
    let active = true; setLoading(true); setError('');
    api<T>(path).then(value => { if (active) setData(value); }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, enabled, revision]);
  return { data, error, loading, refresh: () => setRevision(x => x+1) };
}

export function Loading({ label = 'Getting your workspace ready…' }: { label?: string }) { return <div className="state" role="status"><LoaderCircle className="spin" size={26}/><p>{label}</p></div>; }
export function ErrorState({ message, retry }: { message: string; retry?: () => void }) { return <div className="state error-state" role="alert"><AlertCircle size={28}/><h2>Let’s try that again</h2><p>{message}</p>{retry && <button className="button secondary" onClick={retry}>Try again</button>}</div>; }
export function Empty({ title: heading, children }: { title: string; children?: ReactNode }) { return <div className="state empty"><div className="empty-art"><span/><span/><span/></div><h3>{heading}</h3><p>{children || 'A little space for what comes next.'}</p></div>; }
export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) { return <span className={`badge ${tone}`}>{children}</span>; }
export function StageBadge({ stage }: { stage: string }) { const { settings } = useApp(); return <Badge tone={stage}>{settings.stages.find(s => s.key === stage)?.label || title(stage)}</Badge>; }
export function Avatar({ name, size = '' }: { name: string; size?: string }) { return <span className={`avatar ${size}`} aria-hidden="true">{initials(name)}</span>; }
export function PageHeading({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) { return <div className="page-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="heading-actions">{actions}</div>}</div>; }
export function Stat({ label, value, note, icon }: { label: string; value: ReactNode; note: ReactNode; icon?: ReactNode }) { return <section className="stat"><div className="stat-label">{label}{icon}</div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></section>; }
export function FormError({ error }: { error: string }) { return error ? <div className="form-error" role="alert"><AlertCircle size={17}/><span>{error}</span></div> : null; }
export function SaveButton({ busy, children = 'Save changes' }: { busy: boolean; children?: ReactNode }) { return <button className="button" type="submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17}/> : <Check size={17}/>} {busy ? 'Saving…' : children}</button>; }
export function Modal({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close(); }, []);
  return <dialog ref={ref} className={`modal ${wide ? 'wide' : ''}`} aria-labelledby="dialog-title" onCancel={onClose}><div className="modal-heading"><h2 id="dialog-title">{title}</h2><button type="button" className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={20}/></button></div>{children}</dialog>;
}
export function SectionHeading({ title, detail }: { title: string; detail?: ReactNode }) { return <div className="section-heading"><h2>{title}</h2>{detail && <span>{detail}</span>}</div>; }
export function TextLink({ children }: { children: ReactNode }) { return <span className="text-link">{children}<ArrowRight size={16}/></span>; }