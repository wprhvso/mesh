<script>
  import { onMount } from 'svelte';

  let currentTab = 'clients';
  let me = null;
  let loading = true;
  let error = null;

  let clients = [];
  let runners = [];
  let donors = [];
  let sshKeys = [];
  let dnsRecords = [];

  let showAddClientModal = false;
  let newClientName = '';
  let newClientIsAdmin = false;

  let showAddDonorModal = false;
  let newDonorUser = '';
  let newDonorPat = '';
  let newDonorRepo = 'wprhvso/mesh';

  let showAddSshModal = false;
  let newSshTitle = '';
  let newSshKey = '';

  let qrModalContent = null;

  async function fetchMe() {
    try {
      const res = await fetch('/api/me');
      if (!res.ok) {
        error = `Access denied (${res.status}). Ensure you are connected via AmneziaWG VPN.`;
        loading = false;
        return;
      }
      me = await res.json();
      if (!me.is_admin) {
        currentTab = 'portal';
      }
      loading = false;
    } catch (e) {
      error = e.message;
      loading = false;
    }
  }

  async function loadData() {
    if (!me) return;
    if (me.is_admin) {
      try {
        const [cRes, rRes, dRes, sRes, dnsRes] = await Promise.all([
          fetch('/api/clients').then(r => r.json()),
          fetch('/api/runners').then(r => r.json()),
          fetch('/api/donors').then(r => r.json()),
          fetch('/api/ssh').then(r => r.json()),
          fetch('/api/dns').then(r => r.json())
        ]);
        clients = cRes;
        runners = rRes;
        donors = dRes;
        sshKeys = sRes;
        dnsRecords = dnsRes;
      } catch (e) {
        console.error(e);
      }
    }
  }

  onMount(async () => {
    await fetchMe();
    await loadData();
    setInterval(loadData, 5000);
  });

  async function createClient() {
    if (!newClientName) return;
    await fetch('/api/clients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newClientName, is_admin: newClientIsAdmin })
    });
    newClientName = '';
    newClientIsAdmin = false;
    showAddClientModal = false;
    await loadData();
  }

  async function toggleClient(id, isActive) {
    await fetch(`/api/clients/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive })
    });
    await loadData();
  }

  async function toggleAdmin(id, isAdmin) {
    await fetch(`/api/clients/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_admin: isAdmin })
    });
    await loadData();
  }

  async function deleteClient(id) {
    if (!confirm('Are you sure you want to revoke this client?')) return;
    await fetch(`/api/clients/${id}`, { method: 'DELETE' });
    await loadData();
  }

  async function showQR(id) {
    const res = await fetch(`/api/clients/${id}/qr`);
    const data = await res.json();
    qrModalContent = data;
  }

  async function createDonor() {
    if (!newDonorPat) return;
    await fetch('/api/donors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: newDonorUser, pat_token: newDonorPat, repo_name: newDonorRepo })
    });
    newDonorUser = '';
    newDonorPat = '';
    showAddDonorModal = false;
    await loadData();
  }

  async function deleteDonor(id) {
    if (!confirm('Remove donor account?')) return;
    await fetch(`/api/donors/${id}`, { method: 'DELETE' });
    await loadData();
  }

  async function dispatchDonor(id) {
    await fetch(`/api/donors/${id}/dispatch`, { method: 'POST' });
    alert('Workflow dispatch triggered!');
    await loadData();
  }

  async function createSsh() {
    if (!newSshKey) return;
    await fetch('/api/ssh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newSshTitle, public_key: newSshKey })
    });
    newSshTitle = '';
    newSshKey = '';
    showAddSshModal = false;
    await loadData();
  }

  async function deleteSsh(id) {
    if (!confirm('Remove SSH key?')) return;
    await fetch(`/api/ssh/${id}`, { method: 'DELETE' });
    await loadData();
  }
</script>

<main class="app-container">
  <header class="navbar">
    <div class="brand">
      <span class="logo-mesh">MESH</span>
      <span class="logo-sub">// CONTROL PLANE</span>
    </div>
    {#if me}
      <div class="user-badge">
        <span class="indicator-dot online"></span>
        <span class="user-domain">{me.client.domain}</span>
        <span class="user-ip">({me.client.ip})</span>
        {#if me.is_admin}
          <span class="badge badge-admin">ADMIN</span>
        {:else}
          <span class="badge badge-user">CLIENT</span>
        {/if}
      </div>
    {/if}
  </header>

  {#if loading}
    <div class="center-box">
      <div class="spinner"></div>
      <p>Loading mesh environment...</p>
    </div>
  {:else if error}
    <div class="center-box error-box">
      <h2>Access Denied</h2>
      <p>{error}</p>
      <small>Connect to AmneziaWG VPN (endpoint: 91.230.210.17:51820) to access server.mesh.</small>
    </div>
  {:else}
    {#if me.is_admin}
      <nav class="tab-bar">
        <button class:active={currentTab === 'clients'} on:click={() => currentTab = 'clients'}>Clients ({clients.length})</button>
        <button class:active={currentTab === 'runners'} on:click={() => currentTab = 'runners'}>Runners ({runners.filter(r => r.healthy).length}/{runners.length})</button>
        <button class:active={currentTab === 'donors'} on:click={() => currentTab = 'donors'}>GitHub Donors ({donors.length})</button>
        <button class:active={currentTab === 'ssh'} on:click={() => currentTab = 'ssh'}>SSH Keys ({sshKeys.length})</button>
        <button class:active={currentTab === 'dns'} on:click={() => currentTab = 'dns'}>DNS Zone (.mesh)</button>
        <button class:active={currentTab === 'portal'} on:click={() => currentTab = 'portal'}>My Device</button>
      </nav>
    {/if}

    <div class="content-area">
      {#if currentTab === 'portal'}
        <div class="panel-section">
          <h2>User Device Dashboard</h2>
          <div class="card-grid">
            <div class="card">
              <h3>Profile</h3>
              <p><strong>Device:</strong> {me.client.name}</p>
              <p><strong>Mesh Domain:</strong> <a href="http://{me.client.domain}" target="_blank">{me.client.domain}</a></p>
              <p><strong>Tunnel IP:</strong> {me.client.ip}</p>
              <p><strong>Gateway:</strong> server.mesh (10.10.1.1)</p>
              <div class="btn-group">
                <button class="btn btn-primary" on:click={() => showQR(me.client.id)}>Show QR Code</button>
                <a class="btn btn-secondary" href="/api/clients/{me.client.id}/config" download="{me.client.name}.conf">Download .conf</a>
              </div>
            </div>

            <div class="card">
              <h3>Split Routing Telemetry</h3>
              <p><strong>RU Traffic:</strong> Direct through physical link (91.230.210.17)</p>
              <p><strong>Overseas Traffic:</strong> Multipath ECMP through {runners.filter(r => r.healthy).length} Azure Nodes</p>
              <p><strong>SmartDNS:</strong> 10.10.1.1:53 active</p>
              <p><strong>Cluster Egress:</strong> Microsoft Azure Datacenters</p>
            </div>
          </div>
        </div>

      {:else if currentTab === 'clients'}
        <div class="panel-section">
          <div class="section-header">
            <h2>Connected Clients</h2>
            <button class="btn btn-primary" on:click={() => showAddClientModal = true}>+ New Client</button>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Domain</th>
                <th>IP</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each clients as c}
                <tr>
                  <td><strong>{c.name}</strong></td>
                  <td><code>{c.domain}</code></td>
                  <td><code>{c.ip}</code></td>
                  <td>
                    {#if c.is_admin}
                      <span class="badge badge-admin">Admin</span>
                    {:else}
                      <span class="badge badge-user">User</span>
                    {/if}
                  </td>
                  <td>
                    {#if c.is_active}
                      <span class="badge badge-active">Active</span>
                    {:else}
                      <span class="badge badge-disabled">Disabled</span>
                    {/if}
                  </td>
                  <td>
                    <button class="btn btn-sm" on:click={() => showQR(c.id)}>QR</button>
                    <a class="btn btn-sm" href="/api/clients/{c.id}/config" download="{c.name}.conf">Conf</a>
                    <button class="btn btn-sm" on:click={() => toggleAdmin(c.id, !c.is_admin)}>
                      {c.is_admin ? 'Demote' : 'Make Admin'}
                    </button>
                    <button class="btn btn-sm" on:click={() => toggleClient(c.id, !c.is_active)}>
                      {c.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button class="btn btn-sm btn-danger" on:click={() => deleteClient(c.id)}>Delete</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

      {:else if currentTab === 'runners'}
        <div class="panel-section">
          <div class="section-header">
            <h2>Azure Runner Fleet ({runners.filter(r => r.healthy).length} Online / {runners.length} Total)</h2>
            <button class="btn btn-primary" on:click={() => { donors.forEach(d => dispatchDonor(d.id)); }}>Force Re-dispatch All</button>
          </div>

          <div class="runner-grid">
            {#each runners as r}
              <div class="runner-card" class:runner-healthy={r.healthy}>
                <div class="runner-header">
                  <span class="runner-title">runner{r.node_id}.mesh</span>
                  <span class="indicator-dot" class:online={r.healthy}></span>
                </div>
                <div class="runner-details">
                  <p><strong>Mesh IP:</strong> <code>{r.mesh_ip}</code></p>
                  <p><strong>Overlay IP:</strong> <code>{r.tun_client_ip}</code></p>
                  <p><strong>Azure Egress:</strong> <code>{r.egress_ip || 'Negotiating...'}</code></p>
                  <p><strong>Latency:</strong> {r.ping_ms ? r.ping_ms + ' ms' : 'N/A'}</p>
                  <p class="ssh-hint"><code>ssh runner@{r.mesh_ip}</code></p>
                </div>
              </div>
            {/each}
          </div>
        </div>

      {:else if currentTab === 'donors'}
        <div class="panel-section">
          <div class="section-header">
            <h2>GitHub Donor Accounts (PAT Pool)</h2>
            <button class="btn btn-primary" on:click={() => showAddDonorModal = true}>+ Add Donor Account</button>
          </div>

          <div class="card-grid">
            {#each donors as d}
              <div class="card">
                <h3>{d.username}</h3>
                <p><strong>Repository:</strong> {d.repo_name}</p>
                <p><strong>Target Runners:</strong> {d.target_runners}</p>
                <p><strong>PAT:</strong> <code>{d.pat_token ? d.pat_token.substring(0, 8) + '...' : 'N/A'}</code></p>
                <p><strong>Last Dispatch:</strong> {d.last_dispatched_at || 'Never'}</p>
                <div class="btn-group">
                  <button class="btn btn-primary" on:click={() => dispatchDonor(d.id)}>Dispatch Now</button>
                  <button class="btn btn-danger" on:click={() => deleteDonor(d.id)}>Remove</button>
                </div>
              </div>
            {/each}
          </div>
        </div>

      {:else if currentTab === 'ssh'}
        <div class="panel-section">
          <div class="section-header">
            <h2>Authorized SSH Keys</h2>
            <button class="btn btn-primary" on:click={() => showAddSshModal = true}>+ Add SSH Key</button>
          </div>
          <p class="section-desc">Keys listed here are automatically injected into Server 1 and all active GitHub Actions Azure runners upon boot.</p>

          <table class="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Key Preview</th>
                <th>Added</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each sshKeys as k}
                <tr>
                  <td><strong>{k.title}</strong></td>
                  <td><code>{k.public_key.substring(0, 30)}...{k.public_key.substring(k.public_key.length - 20)}</code></td>
                  <td>{new Date(k.created_at).toLocaleString()}</td>
                  <td>
                    <button class="btn btn-sm btn-danger" on:click={() => deleteSsh(k.id)}>Delete</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

      {:else if currentTab === 'dns'}
        <div class="panel-section">
          <h2>Private DNS Zone (.mesh)</h2>
          <p class="section-desc">Managed natively by SmartDNS at <code>10.10.1.1:53</code>. Reconciled every 5 seconds.</p>

          <table class="data-table">
            <thead>
              <tr>
                <th>Record Domain</th>
                <th>Resolved IP</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {#each dnsRecords as rec}
                <tr>
                  <td><code>{rec.domain}</code></td>
                  <td><code>{rec.ip}</code></td>
                  <td>{rec.description}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}

  {#if showAddClientModal}
    <div class="modal-backdrop">
      <div class="modal">
        <h3>Create New Client</h3>
        <label>
          Device / Client Name:
          <input type="text" bind:value={newClientName} placeholder="e.g. goose, phone, laptop" />
        </label>
        <p class="hint">Domain will be automatically registered as <code>{newClientName ? newClientName + '.mesh' : '<name>.mesh'}</code></p>
        <label class="checkbox-label">
          <input type="checkbox" bind:checked={newClientIsAdmin} />
          Grant Administrator Privileges (is_admin)
        </label>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={() => showAddClientModal = false}>Cancel</button>
          <button class="btn btn-primary" on:click={createClient}>Create</button>
        </div>
      </div>
    </div>
  {/if}

  {#if showAddDonorModal}
    <div class="modal-backdrop">
      <div class="modal">
        <h3>Add GitHub Donor Account</h3>
        <label>
          GitHub Username:
          <input type="text" bind:value={newDonorUser} placeholder="e.g. wprhvso" />
        </label>
        <label>
          Personal Access Token (PAT):
          <input type="password" bind:value={newDonorPat} placeholder="ghp_..." />
        </label>
        <label>
          Workflow Repository:
          <input type="text" bind:value={newDonorRepo} placeholder="username/mesh" />
        </label>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={() => showAddDonorModal = false}>Cancel</button>
          <button class="btn btn-primary" on:click={createDonor}>Save Donor</button>
        </div>
      </div>
    </div>
  {/if}

  {#if showAddSshModal}
    <div class="modal-backdrop">
      <div class="modal">
        <h3>Add Public SSH Key</h3>
        <label>
          Title:
          <input type="text" bind:value={newSshTitle} placeholder="e.g. work-laptop" />
        </label>
        <label>
          Public Key (ssh-ed25519 or ssh-rsa):
          <textarea bind:value={newSshKey} rows="4" placeholder="ssh-ed25519 AAAAC3..."></textarea>
        </label>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={() => showAddSshModal = false}>Cancel</button>
          <button class="btn btn-primary" on:click={createSsh}>Add Key</button>
        </div>
      </div>
    </div>
  {/if}

  {#if qrModalContent}
    <div class="modal-backdrop">
      <div class="modal qr-modal">
        <h3>Client Configuration: {qrModalContent.name}</h3>
        <div class="qr-container">
          <img src={qrModalContent.qr_url} alt="AmneziaWG QR Code" />
        </div>
        <p class="hint">Scan with AmneziaWG app on mobile, or download the configuration file.</p>
        <textarea readonly rows="6" class="conf-box">{qrModalContent.config_text}</textarea>
        <div class="modal-actions">
          <a class="btn btn-primary" href="/api/clients/{qrModalContent.id}/config" download="{qrModalContent.name}.conf">Download .conf</a>
          <button class="btn btn-secondary" on:click={() => qrModalContent = null}>Close</button>
        </div>
      </div>
    </div>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background-color: #0f1117;
    color: #e2e8f0;
  }
  .app-container {
    max-width: 1300px;
    margin: 0 auto;
    padding: 20px;
  }
  .navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 20px;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 20px;
  }
  .brand {
    font-size: 1.5rem;
    font-weight: 800;
  }
  .logo-mesh {
    color: #38bdf8;
    letter-spacing: 2px;
  }
  .logo-sub {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-left: 8px;
    font-weight: 500;
  }
  .user-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #1e293b;
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 0.9rem;
  }
  .indicator-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #64748b;
  }
  .indicator-dot.online {
    background: #22c55e;
    box-shadow: 0 0 8px #22c55e;
  }
  .badge {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
  }
  .badge-admin { background: #8b5cf6; color: white; }
  .badge-user { background: #3b82f6; color: white; }
  .badge-active { background: #166534; color: #86efac; }
  .badge-disabled { background: #7f1d1d; color: #fca5a5; }
  .tab-bar {
    display: flex;
    gap: 8px;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 24px;
  }
  .tab-bar button {
    background: transparent;
    border: none;
    color: #94a3b8;
    padding: 10px 18px;
    font-size: 0.95rem;
    cursor: pointer;
    border-bottom: 2px solid transparent;
  }
  .tab-bar button.active {
    color: #38bdf8;
    border-bottom-color: #38bdf8;
    font-weight: 600;
  }
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 20px;
  }
  .card {
    background: #1e293b;
    border-radius: 8px;
    padding: 20px;
    border: 1px solid #334155;
  }
  .card h3 { margin-top: 0; color: #f8fafc; }
  .btn {
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.9rem;
    cursor: pointer;
    border: none;
    text-decoration: none;
    display: inline-block;
  }
  .btn-primary { background: #38bdf8; color: #0f172a; font-weight: 600; }
  .btn-secondary { background: #334155; color: #e2e8f0; }
  .btn-danger { background: #ef4444; color: white; }
  .btn-sm { padding: 4px 10px; font-size: 0.8rem; margin-right: 4px; }
  .btn-group { display: flex; gap: 10px; margin-top: 16px; }
  .data-table {
    width: 100%;
    border-collapse: collapse;
    background: #1e293b;
    border-radius: 8px;
    overflow: hidden;
  }
  .data-table th, .data-table td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid #334155;
  }
  .data-table th { background: #0f172a; color: #94a3b8; font-size: 0.85rem; }
  .runner-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 16px;
  }
  .runner-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 14px;
  }
  .runner-card.runner-healthy {
    border-color: #22c55e44;
  }
  .runner-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 700;
    margin-bottom: 10px;
    color: #38bdf8;
  }
  .runner-details p { margin: 4px 0; font-size: 0.85rem; }
  .ssh-hint { color: #94a3b8; margin-top: 8px; font-size: 0.75rem; }
  .modal-backdrop {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }
  .modal {
    background: #1e293b;
    border-radius: 8px;
    padding: 24px;
    width: 100%;
    max-width: 480px;
    border: 1px solid #475569;
  }
  .modal label {
    display: block;
    margin-top: 14px;
    font-size: 0.9rem;
    color: #cbd5e1;
  }
  .modal input[type="text"], .modal input[type="password"], .modal textarea {
    width: 100%;
    box-sizing: border-box;
    background: #0f172a;
    border: 1px solid #475569;
    color: white;
    padding: 8px;
    border-radius: 4px;
    margin-top: 6px;
  }
  .checkbox-label {
    display: flex !important;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
  }
  .qr-modal { text-align: center; }
  .qr-container img { width: 220px; height: 220px; margin: 16px auto; background: white; padding: 10px; border-radius: 8px; }
  .conf-box { font-family: monospace; font-size: 0.75rem; resize: none; background: #0f172a; color: #94a3b8; }
  .hint { font-size: 0.8rem; color: #94a3b8; }
  .center-box { text-align: center; padding: 60px 20px; }
  .error-box { max-width: 500px; margin: 40px auto; background: #1e293b; border-radius: 8px; border: 1px solid #ef4444; }
  .spinner {
    border: 3px solid #334155;
    border-top: 3px solid #38bdf8;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin: 0 auto 16px;
  }
  @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>
