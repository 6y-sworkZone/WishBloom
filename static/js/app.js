const API_BASE = '/api/v1';

const CATEGORY_COLORS = {
  '爱情': '#f472b6',
  '事业': '#3b82f6',
  '学业': '#22c55e',
  '健康': '#06b6d4',
  '家庭': '#f97316',
  '其他': '#a855f7'
};

const CATEGORY_NAMES = {
  '爱情': '爱情',
  '事业': '事业',
  '学业': '学业',
  '健康': '健康',
  '家庭': '家庭',
  '其他': '其他'
};

const CARD_BACKGROUNDS = [
  'var(--card-bg-1)',
  'var(--card-bg-2)',
  'var(--card-bg-3)',
  'var(--card-bg-4)',
  'var(--card-bg-5)',
  'var(--card-bg-6)',
  'var(--card-bg-7)',
  'var(--card-bg-8)'
];

let currentUser = null;
let currentWishes = [];
let page = 1;
let isLoading = false;
let hasMore = true;
let currentCategory = 'all';
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNavigation();
  initModals();
  initInfiniteScroll();
  checkAuth();
  
  if (document.querySelector('.masonry')) {
    loadWishes();
  }
  
  if (document.getElementById('tree-canvas')) {
    initWishTree();
  }
  
  if (document.querySelector('.calendar-container')) {
    initCalendar();
  }
  
  if (document.getElementById('createWishForm')) {
    initCreateWishForm();
  }
  
  if (document.getElementById('loginForm')) {
    initLoginForm();
  }
  
  if (document.getElementById('registerForm')) {
    initRegisterForm();
  }
  
  if (document.querySelector('.profile-stats')) {
    loadUserProfile();
  }
  
  if (document.querySelector('.leaderboard-item')) {
    loadLeaderboard();
  }
});

function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  const toggleBtn = document.getElementById('themeToggle');
  if (toggleBtn) {
    toggleBtn.textContent = savedTheme === 'light' ? '🌙' : '☀️';
    toggleBtn.addEventListener('click', () => {
      const newTheme = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      toggleBtn.textContent = newTheme === 'light' ? '🌙' : '☀️';
    });
  }
}

function initNavigation() {
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const navbarMenu = document.getElementById('navbarMenu');
  
  if (mobileMenuBtn && navbarMenu) {
    mobileMenuBtn.addEventListener('click', () => {
      navbarMenu.classList.toggle('show');
    });
  }
  
  const navbarLinks = document.querySelectorAll('.navbar-link');
  const currentPath = window.location.pathname;
  navbarLinks.forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });
}

function initModals() {
  const modal = document.getElementById('wishModal');
  if (!modal) return;
  
  const closeBtn = modal.querySelector('.modal-close');
  closeBtn.addEventListener('click', () => {
    modal.classList.remove('show');
  });
  
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('show');
    }
  });
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('show')) {
      modal.classList.remove('show');
    }
  });
}

function initInfiniteScroll() {
  window.addEventListener('scroll', () => {
    if (isLoading || !hasMore) return;
    
    const scrollTop = window.scrollY;
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    
    if (scrollTop + windowHeight >= documentHeight - 200) {
      loadWishes();
    }
  });
}

async function checkAuth() {
  const token = localStorage.getItem('wishwall_token');
  if (!token) {
    console.log('Not logged in');
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      currentUser = data;
      updateNavbarForAuth();
    } else {
      console.log('Not logged in');
      localStorage.removeItem('wishwall_token');
    }
  } catch (error) {
    console.log('Not logged in:', error);
    localStorage.removeItem('wishwall_token');
  }
}

function updateNavbarForAuth() {
  const authButtons = document.getElementById('authButtons');
  const userMenu = document.getElementById('userMenu');
  
  if (authButtons && currentUser) {
    authButtons.style.display = 'none';
  }
  
  if (userMenu && currentUser) {
    userMenu.style.display = 'flex';
    const avatar = userMenu.querySelector('.avatar');
    if (avatar) {
      avatar.src = currentUser.avatar || '/static/avatar/default.svg';
      avatar.alt = currentUser.username;
    }
  }
}

async function apiRequest(url, options = {}) {
  const token = localStorage.getItem('wishwall_token');
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json'
    },
    credentials: 'include'
  };
  
  if (token) {
    defaultOptions.headers['Authorization'] = `Bearer ${token}`;
  }
  
  const finalOptions = { ...defaultOptions, ...options };
  if (options.body && typeof options.body !== 'string') {
    finalOptions.body = JSON.stringify(options.body);
  }
  
  try {
    const response = await fetch(`${API_BASE}${url}`, finalOptions);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.message || '请求失败');
    }
    
    return data;
  } catch (error) {
    showNotification(error.message || '网络错误', 'error');
    throw error;
  }
}

async function loadWishes() {
  if (isLoading || !hasMore) return;
  
  isLoading = true;
  showLoader();
  
  try {
    const sortMap = {
      'all': 'latest',
      'latest': 'latest',
      'hottest': 'hottest',
      'most_blessings': 'most_blessings'
    };
    
    const params = new URLSearchParams({
      page: page,
      page_size: 12,
      sort_by: sortMap[currentFilter] || 'latest'
    });
    
    if (currentCategory !== 'all') {
      params.append('category', currentCategory);
    }
    
    const token = localStorage.getItem('wishwall_token');
    const headers = {
      'Content-Type': 'application/json'
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE}/wishes?${params}`, {
      headers: headers
    });
    
    if (!response.ok) {
      throw new Error('请求失败');
    }
    
    const data = await response.json();
    currentWishes = [...currentWishes, ...data.items];
    
    renderWishes(data.items);
    
    page++;
    hasMore = page < data.total_pages;
    
    if (!hasMore) {
      hideLoader();
    }
  } catch (error) {
    console.error('Failed to load wishes:', error);
    showNotification('加载愿望失败，请刷新重试', 'error');
  } finally {
    isLoading = false;
    hideLoader();
  }
}

function renderWishes(wishes) {
  const masonry = document.querySelector('.masonry');
  if (!masonry) return;
  
  wishes.forEach((wish, index) => {
    const card = createWishCard(wish, index);
    masonry.appendChild(card);
  });
}

function createWishCard(wish, index = 0) {
  const card = document.createElement('div');
  card.className = `wish-card ${wish.is_fulfilled ? 'fulfilled' : ''}`;
  card.style.background = CARD_BACKGROUNDS[index % CARD_BACKGROUNDS.length];
  card.style.animationDelay = `${index * 0.1}s`;
  card.dataset.id = wish.id;
  
  card.innerHTML = `
    <div class="wish-card-header">
      <img src="${wish.user?.avatar || '/static/avatar/default.svg'}" 
           alt="${wish.user?.username || '匿名用户'}" 
           class="wish-avatar">
      <div class="wish-user-info">
        <div class="wish-username">${escapeHtml(wish.user?.username || '匿名用户')}</div>
        <div class="wish-time">${formatTime(wish.created_at)}</div>
      </div>
      <span class="wish-category category-${wish.category}">${CATEGORY_NAMES[wish.category] || wish.category}</span>
    </div>
    <div class="wish-content">${escapeHtml(wish.content)}</div>
    <div class="wish-card-footer">
      <div class="wish-stats">
        <span class="wish-stat ${wish.is_liked ? 'liked' : ''}" onclick="toggleLike(${wish.id}, event)">
          <span>${wish.is_liked ? '❤️' : '🤍'}</span>
          <span class="like-count">${wish.likes_count || 0}</span>
        </span>
        <span class="wish-stat" onclick="openWishDetail(${wish.id})">
          <span>💬</span>
          <span>${wish.comments_count || 0}</span>
        </span>
      </div>
      ${wish.is_fulfilled ? '<span style="font-size: 1.2rem;">✨</span>' : ''}
    </div>
  `;
  
  card.addEventListener('click', (e) => {
    if (!e.target.closest('.wish-stat')) {
      openWishDetail(wish.id);
    }
  });
  
  return card;
}

async function toggleLike(wishId, event) {
  event.stopPropagation();
  
  if (!currentUser) {
    showNotification('请先登录', 'info');
    return;
  }
  
  const stat = event.currentTarget;
  const likeCount = stat.querySelector('.like-count');
  const icon = stat.querySelector('span:first-child');
  const isLiked = stat.classList.contains('liked');
  
  try {
    if (isLiked) {
      await apiRequest(`/wishes/${wishId}/unlike`, { method: 'POST' });
      stat.classList.remove('liked');
      icon.textContent = '🤍';
      likeCount.textContent = parseInt(likeCount.textContent) - 1;
    } else {
      await apiRequest(`/wishes/${wishId}/like`, { method: 'POST' });
      stat.classList.add('liked');
      icon.textContent = '❤️';
      likeCount.textContent = parseInt(likeCount.textContent) + 1;
    }
  } catch (error) {
    console.error('Failed to toggle like:', error);
  }
}

async function openWishDetail(wishId) {
  try {
    const wish = await apiRequest(`/wishes/${wishId}`);
    const comments = await apiRequest(`/wishes/${wishId}/comments`);
    
    renderWishModal(wish, comments);
    
    const modal = document.getElementById('wishModal');
    modal.classList.add('show');
  } catch (error) {
    console.error('Failed to load wish detail:', error);
  }
}

function renderWishModal(wish, comments) {
  const modalBody = document.querySelector('#wishModal .modal-body');
  if (!modalBody) return;
  
  modalBody.innerHTML = `
    <div class="wish-card ${wish.is_fulfilled ? 'fulfilled' : ''}" style="margin-bottom: 1.5rem;">
      <div class="wish-card-header">
        <img src="${wish.user?.avatar || '/static/avatar/default.svg'}" 
             alt="${wish.user?.username || '匿名用户'}" 
             class="wish-avatar">
        <div class="wish-user-info">
          <div class="wish-username">${escapeHtml(wish.user?.username || '匿名用户')}</div>
          <div class="wish-time">${formatTime(wish.created_at)}</div>
        </div>
        <span class="wish-category category-${wish.category}">${CATEGORY_NAMES[wish.category] || wish.category}</span>
      </div>
      <div class="wish-content" style="font-size: 1.1rem;">${escapeHtml(wish.content)}</div>
      ${wish.is_fulfilled ? `
        <div style="margin-top: 1rem; padding: 1rem; background: rgba(251, 191, 36, 0.2); border-radius: 12px;">
          <strong>✨ 已实现！</strong>
          <p style="margin-top: 0.5rem; color: var(--text-secondary);">实现时间：${formatTime(wish.fulfilled_at)}</p>
        </div>
      ` : ''}
    </div>
    
    <h3 style="margin-bottom: 1rem; font-size: 1.1rem;">祝福留言 (${comments.length})</h3>
    
    ${currentUser ? `
      <form id="commentForm" style="margin-bottom: 1.5rem;">
        <div class="form-group">
          <textarea class="form-textarea" id="commentContent" placeholder="写下你的祝福..." required></textarea>
        </div>
        <button type="submit" class="btn btn-primary">发送祝福</button>
      </form>
    ` : `<p style="margin-bottom: 1.5rem; color: var(--text-secondary);">请<a href="/login" style="color: var(--primary);">登录</a>后发送祝福</p>`}
    
    <div id="commentsList">
      ${comments.length === 0 ? `
        <div class="empty-state" style="padding: 2rem;">
          <div class="empty-state-icon">💝</div>
          <div class="empty-state-title">暂无祝福</div>
          <p>成为第一个送上祝福的人吧！</p>
        </div>
      ` : comments.map(comment => `
        <div style="display: flex; gap: 0.75rem; padding: 1rem 0; border-bottom: 1px solid var(--border);">
          <img src="${comment.user?.avatar || '/static/avatar/default.svg'}" 
               alt="${comment.user?.username || '匿名'}" 
               style="width: 36px; height: 36px; border-radius: 50%;">
          <div style="flex: 1;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
              <strong>${escapeHtml(comment.user?.username || '匿名')}</strong>
              <span style="font-size: 0.8rem; color: var(--text-muted);">${formatTime(comment.created_at)}</span>
            </div>
            <p style="color: var(--text-primary);">${escapeHtml(comment.content)}</p>
          </div>
        </div>
      `).join('')}
    </div>
  `;
  
  if (currentUser) {
    const commentForm = document.getElementById('commentForm');
    commentForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const content = document.getElementById('commentContent').value.trim();
      
      if (!content) return;
      
      try {
        const newComment = await apiRequest(`/wishes/${wish.id}/comments`, {
          method: 'POST',
          body: { content }
        });
        
        document.getElementById('commentContent').value = '';
        
        const commentsList = document.getElementById('commentsList');
        const newCommentHtml = `
          <div style="display: flex; gap: 0.75rem; padding: 1rem 0; border-bottom: 1px solid var(--border); animation: fadeInUp 0.3s ease-out;">
            <img src="${currentUser.avatar || '/static/avatar/default.svg'}" 
                 alt="${currentUser.username}" 
                 style="width: 36px; height: 36px; border-radius: 50%;">
            <div style="flex: 1;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <strong>${escapeHtml(currentUser.username)}</strong>
                <span style="font-size: 0.8rem; color: var(--text-muted);">刚刚</span>
              </div>
              <p style="color: var(--text-primary);">${escapeHtml(content)}</p>
            </div>
          </div>
        `;
        
        if (commentsList.querySelector('.empty-state')) {
          commentsList.innerHTML = newCommentHtml;
        } else {
          commentsList.insertAdjacentHTML('afterbegin', newCommentHtml);
        }
        
        showNotification('祝福发送成功！', 'success');
      } catch (error) {
        console.error('Failed to post comment:', error);
      }
    });
  }
}

function filterWishes(category) {
  currentCategory = category;
  currentWishes = [];
  page = 1;
  hasMore = true;
  
  const masonry = document.querySelector('.masonry');
  if (masonry) {
    masonry.innerHTML = '';
  }
  
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.category === category);
  });
  
  loadWishes();
}

function filterByStatus(filter) {
  currentFilter = filter;
  currentWishes = [];
  page = 1;
  hasMore = true;
  
  const masonry = document.querySelector('.masonry');
  if (masonry) {
    masonry.innerHTML = '';
  }
  
  document.querySelectorAll('.filter-btn[data-filter]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });
  
  loadWishes();
}

function initCreateWishForm() {
  const form = document.getElementById('createWishForm');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!currentUser) {
      showNotification('请先登录', 'info');
      window.location.href = '/login';
      return;
    }
    
    const title = document.getElementById('wishTitle').value.trim();
    const content = document.getElementById('wishContent').value.trim();
    const category = document.getElementById('wishCategory').value;
    const visibility = document.getElementById('wishVisibility').value;
    const isAnonymous = document.getElementById('isAnonymous').checked;
    
    if (!title || !content || !category || !visibility) {
      showNotification('请填写完整信息', 'error');
      return;
    }
    
    try {
      const wish = await apiRequest('/wishes', {
        method: 'POST',
        body: {
          title,
          content,
          category,
          visibility,
          is_anonymous: isAnonymous
        }
      });
      
      showNotification('许愿成功！愿你的愿望早日实现 ✨', 'success');
      
      setTimeout(() => {
        window.location.href = '/';
      }, 1500);
    } catch (error) {
      console.error('Failed to create wish:', error);
    }
  });
}

function initLoginForm() {
  const form = document.getElementById('loginForm');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
      showNotification('请填写完整信息', 'error');
      return;
    }
    
    try {
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: { username, password }
      });
      
      currentUser = data.user;
      if (data.access_token) {
        localStorage.setItem('wishwall_token', data.access_token);
      }
      showNotification('登录成功！欢迎回来', 'success');
      
      setTimeout(() => {
        window.location.href = '/';
      }, 1000);
    } catch (error) {
      console.error('Login failed:', error);
    }
  });
}

function initRegisterForm() {
  const form = document.getElementById('registerForm');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (!username || !email || !password) {
      showNotification('请填写完整信息', 'error');
      return;
    }
    
    if (password !== confirmPassword) {
      showNotification('两次输入的密码不一致', 'error');
      return;
    }
    
    if (password.length < 6) {
      showNotification('密码长度至少为6位', 'error');
      return;
    }
    
    try {
      const data = await apiRequest('/auth/register', {
        method: 'POST',
        body: { username, email, password }
      });
      
      showNotification('注册成功！欢迎加入许愿树', 'success');
      
      setTimeout(() => {
        window.location.href = '/login';
      }, 1500);
    } catch (error) {
      console.error('Registration failed:', error);
    }
  });
}

let wishesForTree = [];

async function initWishTree() {
  const canvas = document.getElementById('tree-canvas');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  resizeCanvas(canvas);
  
  window.addEventListener('resize', () => {
    resizeCanvas(canvas);
    drawTree(ctx, canvas.width, canvas.height);
    drawLeaves(ctx, wishesForTree, canvas.width, canvas.height);
  });
  
  try {
    const data = await apiRequest('/wishes?page_size=100');
    wishesForTree = data.items;
    
    drawTree(ctx, canvas.width, canvas.height);
    drawLeaves(ctx, wishesForTree, canvas.width, canvas.height);
    
    canvas.addEventListener('click', (e) => handleLeafClick(e, canvas, wishesForTree));
  } catch (error) {
    console.error('Failed to load wishes for tree:', error);
    drawTree(ctx, canvas.width, canvas.height);
  }
}

function resizeCanvas(canvas) {
  const container = canvas.parentElement;
  const rect = container.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';
  
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
}

function drawTree(ctx, width, height) {
  const centerX = width / (2 * (window.devicePixelRatio || 1));
  const groundY = height / (window.devicePixelRatio || 1) - 50;
  const treeHeight = groundY - 100;
  
  ctx.clearRect(0, 0, width, height);
  
  ctx.fillStyle = '#d4a574';
  ctx.beginPath();
  ctx.moveTo(centerX - 40, groundY);
  ctx.lineTo(centerX - 25, groundY - treeHeight * 0.4);
  ctx.quadraticCurveTo(centerX - 20, groundY - treeHeight * 0.5, centerX - 15, groundY - treeHeight * 0.6);
  ctx.lineTo(centerX - 8, groundY - treeHeight);
  ctx.lineTo(centerX + 8, groundY - treeHeight);
  ctx.lineTo(centerX + 15, groundY - treeHeight * 0.6);
  ctx.quadraticCurveTo(centerX + 20, groundY - treeHeight * 0.5, centerX + 25, groundY - treeHeight * 0.4);
  ctx.lineTo(centerX + 40, groundY);
  ctx.closePath();
  ctx.fill();
  
  ctx.strokeStyle = '#c4956a';
  ctx.lineWidth = 2;
  for (let i = 0; i < 5; i++) {
    const y = groundY - (treeHeight * 0.1 * (i + 1));
    ctx.beginPath();
    ctx.moveTo(centerX - 30 + i * 3, y);
    ctx.quadraticCurveTo(centerX, y - 10, centerX + 30 - i * 3, y);
    ctx.stroke();
  }
  
  drawBranch(ctx, centerX, groundY - treeHeight * 0.8, -60, treeHeight * 0.3, 8);
  drawBranch(ctx, centerX, groundY - treeHeight * 0.7, 60, treeHeight * 0.35, 8);
  drawBranch(ctx, centerX, groundY - treeHeight * 0.6, -40, treeHeight * 0.25, 6);
  drawBranch(ctx, centerX, groundY - treeHeight * 0.5, 40, treeHeight * 0.28, 6);
  drawBranch(ctx, centerX, groundY - treeHeight * 0.4, -70, treeHeight * 0.2, 5);
  drawBranch(ctx, centerX, groundY - treeHeight * 0.3, 70, treeHeight * 0.22, 5);
}

function drawBranch(ctx, startX, startY, angle, length, width) {
  const rad = (angle * Math.PI) / 180;
  const endX = startX + Math.cos(rad) * length;
  const endY = startY + Math.sin(rad) * length;
  
  ctx.strokeStyle = '#c4956a';
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(startX, startY);
  ctx.quadraticCurveTo(
    startX + Math.cos(rad) * length * 0.5 + (Math.random() - 0.5) * 20,
    startY + Math.sin(rad) * length * 0.5 + (Math.random() - 0.5) * 20,
    endX,
    endY
  );
  ctx.stroke();
  
  if (length > 30) {
    drawBranch(ctx, endX, endY, angle - 30, length * 0.6, width * 0.7);
    drawBranch(ctx, endX, endY, angle + 30, length * 0.6, width * 0.7);
  }
}

let leafPositions = [];

function drawLeaves(ctx, wishes, width, height) {
  const dpr = window.devicePixelRatio || 1;
  const centerX = width / (2 * dpr);
  const groundY = height / dpr - 50;
  
  leafPositions = [];
  
  wishes.forEach((wish, index) => {
    const angle = -90 + (Math.random() - 0.5) * 120;
    const distance = 80 + Math.random() * 150;
    const rad = (angle * Math.PI) / 180;
    
    const x = centerX + Math.cos(rad) * distance;
    const y = groundY - 200 - Math.sin(rad) * distance + (Math.random() - 0.5) * 50;
    
    const color = wish.is_fulfilled ? '#fbbf24' : CATEGORY_COLORS[wish.category] || CATEGORY_COLORS['其他'];
    
    drawLeaf(ctx, x, y, color, wish.is_fulfilled);
    
    leafPositions.push({ x, y, wish });
  });
}

function drawLeaf(ctx, x, y, color, isFulfilled) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate((Math.random() - 0.5) * 0.5);
  
  const scale = isFulfilled ? 1.2 : 1;
  ctx.scale(scale, scale);
  
  if (isFulfilled) {
    ctx.shadowColor = '#fbbf24';
    ctx.shadowBlur = 15;
  }
  
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(0, 0, 12, 8, 0, 0, Math.PI * 2);
  ctx.fill();
  
  ctx.strokeStyle = 'rgba(0,0,0,0.2)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(-10, 0);
  ctx.lineTo(10, 0);
  ctx.stroke();
  
  ctx.restore();
}

function handleLeafClick(event, canvas, wishes) {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  
  for (const pos of leafPositions) {
    const distance = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
    if (distance < 20) {
      openWishDetail(pos.wish.id);
      return;
    }
  }
}

let currentDate = new Date();
let calendarWishes = [];

async function initCalendar() {
  try {
    const data = await apiRequest('/wishes?page_size=200');
    calendarWishes = data.items;
    
    renderCalendar(currentDate);
    
    document.getElementById('prevMonth').addEventListener('click', () => {
      currentDate.setMonth(currentDate.getMonth() - 1);
      renderCalendar(currentDate);
    });
    
    document.getElementById('nextMonth').addEventListener('click', () => {
      currentDate.setMonth(currentDate.getMonth() + 1);
      renderCalendar(currentDate);
    });
  } catch (error) {
    console.error('Failed to load calendar wishes:', error);
    renderCalendar(currentDate);
  }
}

function renderCalendar(date) {
  const year = date.getFullYear();
  const month = date.getMonth();
  
  const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];
  const weekdayNames = ['日', '一', '二', '三', '四', '五', '六'];
  
  document.querySelector('.calendar-month').textContent = `${year}年 ${monthNames[month]}`;
  
  const grid = document.querySelector('.calendar-grid');
  grid.innerHTML = '';
  
  weekdayNames.forEach(day => {
    const weekdayEl = document.createElement('div');
    weekdayEl.className = 'calendar-weekday';
    weekdayEl.textContent = day;
    grid.appendChild(weekdayEl);
  });
  
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();
  
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;
  
  for (let i = firstDay - 1; i >= 0; i--) {
    const dayEl = createCalendarDay(daysInPrevMonth - i, true);
    grid.appendChild(dayEl);
  }
  
  for (let day = 1; day <= daysInMonth; day++) {
    const currentDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dayEl = createCalendarDay(day, false);
    
    if (isCurrentMonth && today.getDate() === day) {
      dayEl.classList.add('today');
    }
    
    const wishesOnDay = calendarWishes.filter(wish => {
      const wishDate = wish.created_at ? wish.created_at.split('T')[0] : '';
      const fulfilledDate = wish.fulfilled_at ? wish.fulfilled_at.split('T')[0] : '';
      return wishDate === currentDateStr || fulfilledDate === currentDateStr;
    });
    
    if (wishesOnDay.length > 0) {
      const dotsEl = document.createElement('div');
      dotsEl.className = 'calendar-dots';
      
      const hasWish = wishesOnDay.some(w => w.created_at && w.created_at.split('T')[0] === currentDateStr);
      const hasFulfilled = wishesOnDay.some(w => w.fulfilled_at && w.fulfilled_at.split('T')[0] === currentDateStr);
      
      if (hasWish) {
        const dot = document.createElement('span');
        dot.className = 'calendar-dot wish';
        dotsEl.appendChild(dot);
      }
      
      if (hasFulfilled) {
        const dot = document.createElement('span');
        dot.className = 'calendar-dot fulfilled';
        dotsEl.appendChild(dot);
      }
      
      dayEl.appendChild(dotsEl);
      
      dayEl.addEventListener('click', () => showDayWishes(year, month, day, wishesOnDay));
    }
    
    grid.appendChild(dayEl);
  }
  
  const totalCells = firstDay + daysInMonth;
  const remainingCells = 42 - totalCells;
  for (let day = 1; day <= remainingCells; day++) {
    const dayEl = createCalendarDay(day, true);
    grid.appendChild(dayEl);
  }
}

function createCalendarDay(day, isOtherMonth) {
  const dayEl = document.createElement('div');
  dayEl.className = `calendar-day ${isOtherMonth ? 'other-month' : ''}`;
  
  const dateEl = document.createElement('span');
  dateEl.className = 'date';
  dateEl.textContent = day;
  dayEl.appendChild(dateEl);
  
  return dayEl;
}

function showDayWishes(year, month, day, wishes) {
  const modal = document.getElementById('wishModal');
  const modalTitle = modal.querySelector('.modal-title');
  const modalBody = modal.querySelector('.modal-body');
  
  modalTitle.textContent = `${year}年${month + 1}月${day}日 的愿望`;
  
  modalBody.innerHTML = wishes.length === 0 ? `
    <div class="empty-state">
      <div class="empty-state-icon">📅</div>
      <div class="empty-state-title">今天没有愿望</div>
      <p>在这一天许下你的第一个愿望吧！</p>
    </div>
  ` : wishes.map(wish => `
    <div class="wish-card ${wish.is_fulfilled ? 'fulfilled' : ''}" style="margin-bottom: 1rem; cursor: pointer;" onclick="openWishDetail(${wish.id})">
      <div class="wish-card-header">
        <span class="wish-category category-${wish.category}">${CATEGORY_NAMES[wish.category] || wish.category}</span>
        ${wish.is_fulfilled ? '<span style="margin-left: auto;">✨ 已实现</span>' : ''}
      </div>
      <div class="wish-content">${escapeHtml(wish.content)}</div>
      <div class="wish-time">${formatTime(wish.created_at)}</div>
    </div>
  `).join('');
  
  modal.classList.add('show');
}

async function loadUserProfile() {
  if (!currentUser) return;
  
  try {
    const stats = await apiRequest('/users/me/stats');
    
    document.querySelector('.profile-stat-value[data-stat="wishes"]').textContent = stats.total_wishes || 0;
    document.querySelector('.profile-stat-value[data-stat="fulfilled"]').textContent = stats.fulfilled_wishes || 0;
    document.querySelector('.profile-stat-value[data-stat="likes"]').textContent = stats.total_likes || 0;
    document.querySelector('.profile-stat-value[data-stat="comments"]').textContent = stats.total_comments || 0;
  } catch (error) {
    console.error('Failed to load user stats:', error);
  }
}

async function loadLeaderboard() {
  try {
    const data = await apiRequest('/leaderboard');
    const list = document.getElementById('leaderboardList');
    
    if (!list) return;
    
    list.innerHTML = data.map((user, index) => `
      <div class="leaderboard-item">
        <div class="leaderboard-rank rank-${index + 1}">${index + 1}</div>
        <img src="${user.avatar || '/static/avatar/default.svg'}" alt="${user.username}" class="leaderboard-avatar">
        <div class="leaderboard-info">
          <div class="leaderboard-name">${escapeHtml(user.username)}</div>
          <div class="leaderboard-points">${user.points || 0} 积分 · ${user.wishes_count || 0} 个愿望</div>
        </div>
        ${index === 0 ? '👑' : ''}
      </div>
    `).join('');
  } catch (error) {
    console.error('Failed to load leaderboard:', error);
  }
}

function switchCommunityTab(tab) {
  document.querySelectorAll('.community-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tab);
  });
  
  document.querySelectorAll('.community-panel').forEach(p => {
    p.style.display = p.dataset.panel === tab ? 'block' : 'none';
  });
}

function showNotification(message, type = 'info') {
  const container = document.getElementById('notificationContainer');
  if (!container) return;
  
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  
  const icons = {
    success: '✅',
    error: '❌',
    info: 'ℹ️'
  };
  
  notification.innerHTML = `
    <span>${icons[type] || 'ℹ️'}</span>
    <span>${message}</span>
  `;
  
  container.appendChild(notification);
  
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);
  
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 3000);
}

function showLoader() {
  const loader = document.getElementById('loader');
  if (loader) {
    loader.classList.add('show');
  }
}

function hideLoader() {
  const loader = document.getElementById('loader');
  if (loader) {
    loader.classList.remove('show');
  }
}

function formatTime(dateString) {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

async function logout() {
  try {
    await apiRequest('/auth/logout', { method: 'POST' });
    currentUser = null;
    showNotification('已退出登录', 'info');
    setTimeout(() => {
      window.location.href = '/';
    }, 1000);
  } catch (error) {
    console.error('Logout failed:', error);
  }
}
