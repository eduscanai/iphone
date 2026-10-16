import { expect, it } from 'vitest'
import { conteudoQR } from './Cabines'

it('QR de pareamento tem API e código no formato que o app lê', () => {
  expect(JSON.parse(conteudoQR('https://api.exemplo', 'K7PQ-3XWD'))).toEqual({ api: 'https://api.exemplo', codigo: 'K7PQ-3XWD' })
})
