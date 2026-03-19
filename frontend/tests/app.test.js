// frontend/tests/app.test.js
/**
 * @jest-environment jsdom
 */

describe('YouTube URL Validation', () => {
  const isValidYoutubeUrl = url => {
    const patterns = [
      /^https?:\/\/(www\.)?youtube\.com\/watch\?.*v=[\w-]{11}/,
      /^https?:\/\/youtu\.be\/[\w-]{11}/,
      /^https?:\/\/m\.youtube\.com\/watch\?.*v=[\w-]{11}/
    ]
    return patterns.some(pattern => pattern.test(url))
  }

  test('should accept standard YouTube URL', () => {
    expect(
      isValidYoutubeUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    ).toBe(true)
  })

  test('should accept short YouTube URL', () => {
    expect(isValidYoutubeUrl('https://youtu.be/dQw4w9WgXcQ')).toBe(true)
  })

  test('should accept mobile YouTube URL', () => {
    expect(isValidYoutubeUrl('https://m.youtube.com/watch?v=dQw4w9WgXcQ')).toBe(
      true
    )
  })

  test('should reject invalid URL', () => {
    expect(isValidYoutubeUrl('https://vimeo.com/123456')).toBe(false)
  })

  test('should reject empty string', () => {
    expect(isValidYoutubeUrl('')).toBe(false)
  })
})

describe('Text Truncation', () => {
  const truncateText = (text, maxLength) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  test('should not truncate short text', () => {
    expect(truncateText('Hello', 10)).toBe('Hello')
  })

  test('should truncate long text', () => {
    expect(truncateText('Hello World', 5)).toBe('Hello...')
  })
})
