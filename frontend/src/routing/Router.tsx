import { createContext, useContext, useEffect, useMemo, useState, type AnchorHTMLAttributes, type ReactNode } from 'react'

type RouterContextValue = { path: string; navigate: (to: string) => void }
const RouterContext = createContext<RouterContextValue | null>(null)

function normalizePath(path: string) {
  const cleanPath = path.split('?')[0].replace(/\/+$/, '')
  return cleanPath || '/command-center'
}

export function Router({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(() => normalizePath(window.location.pathname))

  useEffect(() => {
    const handlePopState = () => setPath(normalizePath(window.location.pathname))
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const value = useMemo<RouterContextValue>(() => ({
    path,
    navigate: (to) => {
      const nextPath = normalizePath(to)
      if (nextPath === path) return
      window.history.pushState({}, '', nextPath)
      setPath(nextPath)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
  }), [path])

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
}

export function useRouter() {
  const value = useContext(RouterContext)
  if (!value) throw new Error('useRouter must be used inside Router')
  return value
}

export function RouteLink({ to, children, className, onClick, ...props }: { to: string; children: ReactNode; className?: string; onClick?: () => void } & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href' | 'onClick' | 'className' | 'children'>) {
  const { navigate } = useRouter()
  return <a {...props} className={className} href={to} onClick={(event) => { event.preventDefault(); onClick?.(); navigate(to) }}>{children}</a>
}

export function isRoute(path: string, route: string) {
  return path === route || path.startsWith(`${route}/`)
}