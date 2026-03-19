// frontend/js/app.js

/**
 * YouTube to MP3 Converter - Frontend Application
 * Módulo principal com arquitetura limpa e padrões modernos
 */

// ==================== CONFIGURATION ====================
const CONFIG = {
  API_BASE_URL: '/api',
  POLL_INTERVAL: 1000,
  TOAST_DURATION: 4000
}

// ==================== API SERVICE ====================
class ApiService {
  constructor(baseUrl) {
    this.baseUrl = baseUrl
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json'
      },
      ...options
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || `HTTP error ${response.status}`)
      }

      if (response.status === 204) {
        return null
      }

      return await response.json()
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error)
      throw error
    }
  }

  // Links
  async getLinks() {
    return this.request('/links')
  }

  async addLink(url) {
    return this.request('/links', {
      method: 'POST',
      body: JSON.stringify({ url })
    })
  }

  async updateLink(id, url) {
    return this.request(`/links/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ url })
    })
  }

  async deleteLink(id) {
    return this.request(`/links/${id}`, {
      method: 'DELETE'
    })
  }

  async clearLinks() {
    return this.request('/links', {
      method: 'DELETE'
    })
  }

  // Conversion
  async startConversion() {
    return this.request('/convert/start', {
      method: 'POST'
    })
  }

  async stopConversion() {
    return this.request('/convert/stop', {
      method: 'POST'
    })
  }

  async getStatus() {
    return this.request('/convert/status')
  }

  // Download
  getDownloadUrl(taskId) {
    return `${this.baseUrl}/download/${taskId}`
  }
}

// ==================== STATE MANAGEMENT ====================
class Store {
  constructor() {
    this.state = {
      links: [],
      isConverting: false,
      currentTaskId: null
    }
    this.listeners = new Set()
  }

  getState() {
    return { ...this.state }
  }

  setState(newState) {
    this.state = { ...this.state, ...newState }
    this.notify()
  }

  subscribe(listener) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  notify() {
    this.listeners.forEach(listener => listener(this.state))
  }
}

// ==================== UI COMPONENTS ====================
class ToastManager {
  constructor(containerId) {
    this.container = document.getElementById(containerId)
  }

  show(message, type = 'info') {
    const toast = document.createElement('div')
    toast.className = `toast ${type}`
    toast.innerHTML = `
            <svg class="toast-icon" viewBox="0 0 24 24" fill="none">
                ${this.getIcon(type)}
            </svg>
            <span class="toast-message">${message}</span>
            <button class="toast-close">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </button>
        `

    const closeBtn = toast.querySelector('.toast-close')
    closeBtn.addEventListener('click', () => this.remove(toast))

    this.container.appendChild(toast)

    setTimeout(() => this.remove(toast), CONFIG.TOAST_DURATION)
  }

  remove(toast) {
    toast.style.animation = 'slideIn 0.3s ease reverse'
    setTimeout(() => toast.remove(), 300)
  }

  getIcon(type) {
    const icons = {
      success:
        '<path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
      error:
        '<path d="M12 9V13M12 17H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
      info: '<path d="M12 16V12M12 8H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
    }
    return icons[type] || icons.info
  }

  success(message) {
    this.show(message, 'success')
  }

  error(message) {
    this.show(message, 'error')
  }

  info(message) {
    this.show(message, 'info')
  }
}

// ==================== LINK ITEM RENDERER ====================
class LinkRenderer {
  constructor(api, store, toast) {
    this.api = api
    this.store = store
    this.toast = toast
  }

  render(link) {
    const item = document.createElement('div')
    item.className = `link-item ${link.status}`
    item.dataset.id = link.id

    if (link.status === 'completed') {
      item.innerHTML = this.renderCompleted(link)
      this.attachCompletedHandlers(item, link)
    } else {
      item.innerHTML = this.renderPending(link)
      this.attachPendingHandlers(item, link)
    }

    return item
  }

  renderPending(link) {
    const displayUrl = this.truncateUrl(link.url)
    const progress = link.status === 'converting' ? link.progress : 0

    return `
            <div class="link-content">
                <span class="link-url" title="${link.url}">${displayUrl}</span>
                <div class="link-actions">
                    <button class="link-action-btn edit" title="Editar">
                        <svg viewBox="0 0 24 24" fill="none">
                            <path d="M11 4H4C3.44772 4 3 4.44772 3 5V20C3 20.5523 3.44772 21 4 21H19C19.5523 21 20 20.5523 20 20V13M18.5 2.5C19.3284 1.67157 20.6716 1.67157 21.5 2.5C22.3284 3.32843 22.3284 4.67157 21.5 5.5L12 15L8 16L9 12L18.5 2.5Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <button class="link-action-btn delete" title="Remover">
                        <svg viewBox="0 0 24 24" fill="none">
                            <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </button>
                </div>
            </div>
            ${
              link.status === 'converting'
                ? `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
            `
                : ''
            }
        `
  }

  renderCompleted(link) {
    const title = link.title || 'Baixar MP3'

    return `
            <div class="link-content">
                <div class="download-text">
                    <svg viewBox="0 0 24 24" fill="none">
                        <path d="M21 15V19C21 20.1046 20.1046 21 19 21H5C3.89543 21 3 20.1046 3 19V15M7 10L12 15M12 15L17 10M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span>BAIXAR MP3</span>
                </div>
                <span class="link-url" title="${link.title}">${this.truncateText(title, 30)}</span>
                <div class="link-actions">
                    <button class="link-action-btn delete" title="Remover">
                        <svg viewBox="0 0 24 24" fill="none">
                            <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </button>
                </div>
            </div>
        `
  }

  attachPendingHandlers(item, link) {
    const editBtn = item.querySelector('.edit')
    const deleteBtn = item.querySelector('.delete')

    if (editBtn) {
      editBtn.addEventListener('click', e => {
        e.stopPropagation()
        this.handleEdit(item, link)
      })
    }

    deleteBtn.addEventListener('click', e => {
      e.stopPropagation()
      this.handleDelete(link.id)
    })
  }

  attachCompletedHandlers(item, link) {
    const deleteBtn = item.querySelector('.delete')
    const content = item.querySelector('.link-content')

    content.addEventListener('click', e => {
      if (!e.target.closest('.delete')) {
        this.handleDownload(link.id)
      }
    })

    deleteBtn.addEventListener('click', e => {
      e.stopPropagation()
      this.handleDelete(link.id)
    })
  }

  handleEdit(item, link) {
    const content = item.querySelector('.link-content')
    const urlSpan = item.querySelector('.link-url')

    // Replace with input
    const input = document.createElement('input')
    input.type = 'text'
    input.className = 'link-edit-input'
    input.value = link.url

    urlSpan.replaceWith(input)
    input.focus()
    input.select()

    const saveEdit = async () => {
      const newUrl = input.value.trim()

      if (newUrl && newUrl !== link.url) {
        try {
          await this.api.updateLink(link.id, newUrl)
          this.toast.success('Link atualizado')
          window.app.loadLinks()
        } catch (error) {
          this.toast.error('Erro ao atualizar link')
          window.app.loadLinks()
        }
      } else {
        window.app.loadLinks()
      }
    }

    input.addEventListener('blur', saveEdit)
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault()
        saveEdit()
      } else if (e.key === 'Escape') {
        window.app.loadLinks()
      }
    })
  }

  async handleDelete(id) {
    try {
      await this.api.deleteLink(id)
      this.toast.success('Link removido')
      window.app.loadLinks()
    } catch (error) {
      this.toast.error('Erro ao remover link')
    }
  }

  handleDownload(id) {
    const url = this.api.getDownloadUrl(id)
    const a = document.createElement('a')
    a.href = url
    a.download = ''
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    this.toast.success('Download iniciado')
  }

  truncateUrl(url) {
    const maxLength = 50
    if (url.length <= maxLength) return url
    return url.substring(0, maxLength) + '...'
  }

  truncateText(text, maxLength) {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }
}

// ==================== MAIN APPLICATION ====================
class App {
  constructor() {
    this.api = new ApiService(CONFIG.API_BASE_URL)
    this.store = new Store()
    this.toast = new ToastManager('toastContainer')
    this.linkRenderer = new LinkRenderer(this.api, this.store, this.toast)

    this.pollInterval = null

    this.elements = {
      urlInput: document.getElementById('urlInput'),
      addBtn: document.getElementById('addBtn'),
      convertBtn: document.getElementById('convertBtn'),
      clearBtn: document.getElementById('clearBtn'),
      linksList: document.getElementById('linksList'),
      emptyState: document.getElementById('emptyState'),
      linksCount: document.getElementById('linksCount'),
      pendingCount: document.getElementById('pendingCount'),
      completedCount: document.getElementById('completedCount')
    }

    this.init()
  }

  init() {
    this.bindEvents()
    this.loadLinks()
    this.store.subscribe(state => this.render(state))
  }

  bindEvents() {
    // Add link
    this.elements.addBtn.addEventListener('click', () => this.addLink())
    this.elements.urlInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault()
        this.addLink()
      }
    })

    // Convert
    this.elements.convertBtn.addEventListener('click', () =>
      this.toggleConversion()
    )

    // Clear
    this.elements.clearBtn.addEventListener('click', () => this.clearAll())
  }

  async loadLinks() {
    try {
      const links = await this.api.getLinks()
      const status = await this.api.getStatus()

      this.store.setState({
        links,
        isConverting: status.is_converting,
        currentTaskId: status.current_task_id
      })

      if (status.is_converting) {
        this.startPolling()
      }
    } catch (error) {
      this.toast.error('Erro ao carregar links')
    }
  }

  async addLink() {
    const url = this.elements.urlInput.value.trim()

    if (!url) {
      this.toast.error('Por favor, insira uma URL')
      return
    }

    if (!this.isValidYoutubeUrl(url)) {
      this.toast.error('URL do YouTube inválida')
      return
    }

    try {
      await this.api.addLink(url)
      this.elements.urlInput.value = ''
      this.toast.success('Link adicionado')
      this.loadLinks()
    } catch (error) {
      this.toast.error(error.message || 'Erro ao adicionar link')
    }
  }

  async toggleConversion() {
    const state = this.store.getState()

    if (state.isConverting) {
      await this.stopConversion()
    } else {
      await this.startConversion()
    }
  }

  async startConversion() {
    try {
      await this.api.startConversion()
      this.store.setState({ isConverting: true })
      this.toast.info('Conversão iniciada')
      this.startPolling()
    } catch (error) {
      this.toast.error(error.message || 'Erro ao iniciar conversão')
    }
  }

  async stopConversion() {
    try {
      await this.api.stopConversion()
      this.stopPolling()
      this.store.setState({ isConverting: false, currentTaskId: null })
      this.toast.info('Conversão parada')
      this.loadLinks()
    } catch (error) {
      this.toast.error('Erro ao parar conversão')
    }
  }

  async clearAll() {
    if (!confirm('Tem certeza que deseja remover todos os links e arquivos?')) {
      return
    }

    try {
      this.stopPolling()
      await this.api.clearLinks()
      this.store.setState({
        links: [],
        isConverting: false,
        currentTaskId: null
      })
      this.toast.success('Tudo limpo')
    } catch (error) {
      this.toast.error('Erro ao limpar')
    }
  }

  startPolling() {
    if (this.pollInterval) return

    this.pollInterval = setInterval(async () => {
      try {
        const links = await this.api.getLinks()
        const status = await this.api.getStatus()

        this.store.setState({
          links,
          isConverting: status.is_converting,
          currentTaskId: status.current_task_id
        })

        if (!status.is_converting) {
          this.stopPolling()
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }, CONFIG.POLL_INTERVAL)
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval)
      this.pollInterval = null
    }
  }

  render(state) {
    // Update counts
    const pending = state.links.filter(l => l.status === 'pending').length
    const completed = state.links.filter(l => l.status === 'completed').length

    this.elements.linksCount.textContent = state.links.length
    this.elements.pendingCount.textContent = pending
    this.elements.completedCount.textContent = completed

    // Update input state
    this.elements.urlInput.disabled = state.isConverting
    this.elements.addBtn.disabled = state.isConverting

    // Update convert button
    if (state.isConverting) {
      this.elements.convertBtn.classList.add('converting')
      this.elements.convertBtn.innerHTML = `
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                    <rect x="6" y="6" width="12" height="12" stroke="currentColor" stroke-width="2"/>
                </svg>
                <span>PARAR</span>
            `
    } else {
      this.elements.convertBtn.classList.remove('converting')
      this.elements.convertBtn.innerHTML = `
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                    <path d="M4 12L20 12M20 12L14 6M20 12L14 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>CONVERTER</span>
            `
    }

    // Update links list
    this.renderLinks(state.links)
  }

  renderLinks(links) {
    // Clear current links (keep empty state)
    const items = this.elements.linksList.querySelectorAll('.link-item')
    items.forEach(item => item.remove())

    if (links.length === 0) {
      this.elements.emptyState.style.display = 'flex'
      return
    }

    this.elements.emptyState.style.display = 'none'

    // Render links in order
    links.forEach(link => {
      const item = this.linkRenderer.render(link)
      this.elements.linksList.appendChild(item)
    })
  }

  isValidYoutubeUrl(url) {
    const patterns = [
      /^https?:\/\/(www\.)?youtube\.com\/watch\?.*v=[\w-]{11}/,
      /^https?:\/\/youtu\.be\/[\w-]{11}/,
      /^https?:\/\/m\.youtube\.com\/watch\?.*v=[\w-]{11}/
    ]
    return patterns.some(pattern => pattern.test(url))
  }
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App()
})
