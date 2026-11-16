import type { Band } from '../api/types'

export const BAND_BADGE: Record<Band, string> = {
  strong: 'bg-success-weak text-success',
  good: 'bg-primary-weak text-primary',
  fair: 'bg-warn-weak text-warn',
  weak: 'bg-danger-weak text-danger',
}

export const BAND_LABEL: Record<Band, string> = {
  strong: 'Strong match',
  good: 'Good match',
  fair: 'Fair match',
  weak: 'Weak match',
}

export const bandForScore = (score: number): Band =>
  score >= 80 ? 'strong' : score >= 60 ? 'good' : score >= 40 ? 'fair' : 'weak'
