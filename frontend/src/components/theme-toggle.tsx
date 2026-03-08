import { Moon, Sun } from '@phosphor-icons/react'
import { Button } from '@/components/ui/button'
import { useTheme } from './theme-provider'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
      className="rounded-full"
    >
      {theme === 'light' ? (
        <Moon className="h-5 w-5" weight="bold" />
      ) : (
        <Sun className="h-5 w-5" weight="bold" />
      )}
      <span className="sr-only">Toggle theme</span>
    </Button>
  )
}
