<script setup>
import {
  MessageCircle, Bell, Clock3, Wifi, LockKeyhole, LogOut, Info, Search,
  X, ChevronLeft, ChevronRight, Check, CheckCheck, RefreshCw, Menu,
  QrCode, CircleAlert, ArrowUpRight, LoaderCircle, Smartphone, ShieldCheck,
  Star, Tag, Archive, ArchiveRestore,
} from 'lucide-vue-next'

defineProps({ name: { type: String, default: 'message' }, size: { type: [Number, String], default: 22 } })
const icons = {
  message: MessageCircle, bell: Bell, history: Clock3, connection: Wifi,
  lock: LockKeyhole, logout: LogOut, info: Info, search: Search, close: X,
  previous: ChevronLeft, next: ChevronRight, check: Check, seen: CheckCheck,
  refresh: RefreshCw, menu: Menu, qr: QrCode, alert: CircleAlert,
  arrow: ArrowUpRight, loading: LoaderCircle, phone: Smartphone, shield: ShieldCheck,
  star: Star, tag: Tag, archive: Archive, restore: ArchiveRestore,
}
</script>

<template>
  <component :is="icons[name] || icons.message" :size="size" :stroke-width="1.7" aria-hidden="true" />
</template>
