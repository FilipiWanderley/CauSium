import { useEffect, useRef, useState } from 'react'
import { Camera } from 'lucide-react'

const STORAGE_KEY = 'stratopulse:avatar'

interface Props {
  name: string
  size?: 'sm' | 'md'
}

function getInitials(name: string) {
  const parts = name.trim().split(' ')
  if (parts.length === 1) return parts[0][0]?.toUpperCase() ?? '?'
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function UserAvatar({ name, size = 'md' }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [src, setSrc] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY))

  const dim = size === 'sm' ? 'h-7 w-7 text-xs' : 'h-9 w-9 text-sm'

  useEffect(() => {
    const onUpdate = () => setSrc(localStorage.getItem(STORAGE_KEY))
    window.addEventListener('avatar-updated', onUpdate)
    return () => window.removeEventListener('avatar-updated', onUpdate)
  }, [])

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      localStorage.setItem(STORAGE_KEY, dataUrl)
      setSrc(dataUrl)
      window.dispatchEvent(new Event('avatar-updated'))
    }
    reader.readAsDataURL(file)
  }

  return (
    <button
      type="button"
      onClick={() => inputRef.current?.click()}
      className={`group relative flex-shrink-0 ${dim} rounded-full overflow-hidden ring-2 ring-gray-200 hover:ring-brand-400 transition-all`}
      title="Clique para alterar a foto"
    >
      {src ? (
        <img src={src} alt={name} className="h-full w-full object-cover" />
      ) : (
        <span className="flex h-full w-full items-center justify-center bg-brand-500 font-semibold text-white">
          {getInitials(name)}
        </span>
      )}
      <span className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
        <Camera className="h-3.5 w-3.5 text-white" />
      </span>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFile}
      />
    </button>
  )
}
