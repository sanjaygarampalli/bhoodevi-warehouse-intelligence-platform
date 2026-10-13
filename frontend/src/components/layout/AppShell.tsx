import { Sidebar } from '../navigation/Sidebar'
import { TopHeader } from './TopHeader'
import { MobileNavigation } from '../navigation/MobileNavigation'
import { useState, type ReactNode } from 'react'
export function AppShell({ children, onLogout }: { children: ReactNode; onLogout: () => void }) { const [menuOpen, setMenuOpen] = useState(false); return <div className="app-shell"><Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} /><div className="app-main"><TopHeader onMenuOpen={() => setMenuOpen(true)} onLogout={onLogout} />{children}<MobileNavigation /><footer className="app-footer"><span>BWIP | SMARTER TODAY. CONNECTED ALWAYS.</span><span>Internal intelligence platform · F2 foundation</span></footer></div></div> }