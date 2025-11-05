/**
 * Organization Dashboard JavaScript
 * Handles all organization management functionality
 */

function organizationDashboard() {
    return {
        // State
        currentTab: 'overview',
        organization: {},
        quotas: {},
        features: {},
        warnings: [],
        members: [],
        teams: [],
        pendingInvitations: [],
        auditLogs: [],
        recentActivity: [],
        canUpgrade: false,

        // Settings
        settings: {
            name: '',
            contact_email: '',
            contact_phone: '',
            logo_url: '',
            primary_color: '#3b82f6'
        },

        // Forms
        inviteForm: {
            email: '',
            role: 'member'
        },

        // Modals
        modals: {
            invite: false,
            createTeam: false,
            editRole: false,
            delete: false
        },

        // Filters
        auditFilters: {
            action: '',
            user: '',
            startDate: ''
        },

        // API Base URL
        apiBase: '/api/organizations',

        /**
         * Initialize dashboard
         */
        async init() {
            await this.loadOrganization();
            await this.loadUsageStats();
            await this.loadMembers();
            await this.loadTeams();
            await this.loadPendingInvitations();
            await this.loadRecentActivity();
        },

        /**
         * Refresh all data
         */
        async refreshData() {
            await this.init();
            this.showNotification('Data refreshed successfully', 'success');
        },

        /**
         * Load organization details
         */
        async loadOrganization() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}`, {
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.organization = await response.json();

                    // Update settings form
                    this.settings = {
                        name: this.organization.name,
                        contact_email: this.organization.contact_email || '',
                        contact_phone: this.organization.contact_phone || '',
                        logo_url: this.organization.logo_url || '',
                        primary_color: this.organization.primary_color || '#3b82f6'
                    };
                }
            } catch (error) {
                console.error('Error loading organization:', error);
                this.showNotification('Failed to load organization', 'error');
            }
        },

        /**
         * Load usage statistics and quotas
         */
        async loadUsageStats() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/usage`, {
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    const data = await response.json();
                    this.quotas = data.quotas || {};
                    this.features = data.features || {};
                    this.warnings = data.warnings || [];

                    // Check if can upgrade
                    this.canUpgrade = this.organization.plan !== 'enterprise';
                }
            } catch (error) {
                console.error('Error loading usage stats:', error);
            }
        },

        /**
         * Load organization members
         */
        async loadMembers() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/members?limit=100`, {
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.members = await response.json();
                }
            } catch (error) {
                console.error('Error loading members:', error);
            }
        },

        /**
         * Load teams
         */
        async loadTeams() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/teams?limit=100`, {
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.teams = await response.json();
                }
            } catch (error) {
                console.error('Error loading teams:', error);
            }
        },

        /**
         * Load pending invitations
         */
        async loadPendingInvitations() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/invitations?status=pending`, {
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.pendingInvitations = await response.json();
                }
            } catch (error) {
                console.error('Error loading invitations:', error);
            }
        },

        /**
         * Load recent activity from audit logs
         */
        async loadRecentActivity() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/audit-logs?limit=10`, {
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.recentActivity = await response.json();
                }
            } catch (error) {
                console.error('Error loading recent activity:', error);
            }
        },

        /**
         * Load audit logs with filters
         */
        async loadAuditLogs() {
            try {
                const orgId = this.getOrganizationId();
                const params = new URLSearchParams({
                    limit: 100,
                    ...(this.auditFilters.action && { action: this.auditFilters.action }),
                    ...(this.auditFilters.user && { user: this.auditFilters.user }),
                    ...(this.auditFilters.startDate && { start_date: this.auditFilters.startDate })
                });

                const response = await fetch(`${this.apiBase}/${orgId}/audit-logs?${params}`, {
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.auditLogs = await response.json();
                }
            } catch (error) {
                console.error('Error loading audit logs:', error);
                this.showNotification('Failed to load audit logs', 'error');
            }
        },

        /**
         * Show invite modal
         */
        showInviteModal() {
            this.inviteForm = { email: '', role: 'member' };
            this.modals.invite = true;
        },

        /**
         * Send invitation
         */
        async sendInvitation() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/invitations`, {
                    method: 'POST',
                    headers: this.getHeaders(),
                    body: JSON.stringify(this.inviteForm)
                });

                if (response.ok) {
                    this.showNotification('Invitation sent successfully', 'success');
                    this.modals.invite = false;
                    await this.loadPendingInvitations();
                } else {
                    const error = await response.json();
                    this.showNotification(error.detail || 'Failed to send invitation', 'error');
                }
            } catch (error) {
                console.error('Error sending invitation:', error);
                this.showNotification('Failed to send invitation', 'error');
            }
        },

        /**
         * Resend invitation
         */
        async resendInvitation(invitationId) {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/invitations/${invitationId}/resend`, {
                    method: 'POST',
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.showNotification('Invitation resent', 'success');
                } else {
                    this.showNotification('Failed to resend invitation', 'error');
                }
            } catch (error) {
                console.error('Error resending invitation:', error);
            }
        },

        /**
         * Cancel invitation
         */
        async cancelInvitation(invitationId) {
            if (!confirm('Are you sure you want to cancel this invitation?')) {
                return;
            }

            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/invitations/${invitationId}`, {
                    method: 'DELETE',
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.showNotification('Invitation cancelled', 'success');
                    await this.loadPendingInvitations();
                } else {
                    this.showNotification('Failed to cancel invitation', 'error');
                }
            } catch (error) {
                console.error('Error cancelling invitation:', error);
            }
        },

        /**
         * Edit member role
         */
        editMemberRole(member) {
            const newRole = prompt(`Enter new role for ${member.username}:`, member.role);
            if (!newRole || newRole === member.role) {
                return;
            }

            this.updateMemberRole(member.user_id, newRole);
        },

        /**
         * Update member role
         */
        async updateMemberRole(userId, newRole) {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/members/${userId}/role`, {
                    method: 'PUT',
                    headers: this.getHeaders(),
                    body: JSON.stringify({ role: newRole })
                });

                if (response.ok) {
                    this.showNotification('Member role updated', 'success');
                    await this.loadMembers();
                } else {
                    const error = await response.json();
                    this.showNotification(error.detail || 'Failed to update role', 'error');
                }
            } catch (error) {
                console.error('Error updating member role:', error);
                this.showNotification('Failed to update role', 'error');
            }
        },

        /**
         * Remove member
         */
        async removeMember(member) {
            if (!confirm(`Are you sure you want to remove ${member.username} from the organization?`)) {
                return;
            }

            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/members/${member.user_id}`, {
                    method: 'DELETE',
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.showNotification('Member removed', 'success');
                    await this.loadMembers();
                } else {
                    const error = await response.json();
                    this.showNotification(error.detail || 'Failed to remove member', 'error');
                }
            } catch (error) {
                console.error('Error removing member:', error);
                this.showNotification('Failed to remove member', 'error');
            }
        },

        /**
         * Show create team modal
         */
        showCreateTeamModal() {
            const name = prompt('Enter team name:');
            if (name) {
                this.createTeam(name);
            }
        },

        /**
         * Create team
         */
        async createTeam(name, description = '') {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/teams`, {
                    method: 'POST',
                    headers: this.getHeaders(),
                    body: JSON.stringify({ name, description })
                });

                if (response.ok) {
                    this.showNotification('Team created successfully', 'success');
                    await this.loadTeams();
                } else {
                    const error = await response.json();
                    this.showNotification(error.detail || 'Failed to create team', 'error');
                }
            } catch (error) {
                console.error('Error creating team:', error);
                this.showNotification('Failed to create team', 'error');
            }
        },

        /**
         * View team details
         */
        viewTeam(team) {
            // Navigate to team detail page or show modal
            alert(`Viewing team: ${team.name}\nMembers: ${team.member_count}`);
            // In production, this would navigate to a detail view
        },

        /**
         * Save organization settings
         */
        async saveSettings() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}`, {
                    method: 'PUT',
                    headers: this.getHeaders(),
                    body: JSON.stringify(this.settings)
                });

                if (response.ok) {
                    this.showNotification('Settings saved successfully', 'success');
                    await this.loadOrganization();
                } else {
                    const error = await response.json();
                    this.showNotification(error.detail || 'Failed to save settings', 'error');
                }
            } catch (error) {
                console.error('Error saving settings:', error);
                this.showNotification('Failed to save settings', 'error');
            }
        },

        /**
         * Show delete confirmation
         */
        showDeleteConfirmation() {
            const confirmation = prompt('Type the organization name to confirm deletion:');
            if (confirmation === this.organization.name) {
                this.deleteOrganization();
            } else if (confirmation) {
                this.showNotification('Organization name did not match', 'error');
            }
        },

        /**
         * Delete organization
         */
        async deleteOrganization() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}`, {
                    method: 'DELETE',
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    this.showNotification('Organization deleted', 'success');
                    // Redirect to organizations list
                    setTimeout(() => {
                        window.location.href = '/organizations';
                    }, 2000);
                } else {
                    const error = await response.json();
                    this.showNotification(error.detail || 'Failed to delete organization', 'error');
                }
            } catch (error) {
                console.error('Error deleting organization:', error);
                this.showNotification('Failed to delete organization', 'error');
            }
        },

        /**
         * Show upgrade modal
         */
        showUpgradeModal() {
            alert('Upgrade functionality - integrate with billing system');
            // In production, this would show upgrade options
        },

        /**
         * Export audit logs
         */
        async exportAuditLogs() {
            try {
                const orgId = this.getOrganizationId();
                const response = await fetch(`${this.apiBase}/${orgId}/audit-logs/export?format=csv`, {
                    headers: this.getHeaders()
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `audit-logs-${orgId}-${new Date().toISOString()}.csv`;
                    a.click();
                    this.showNotification('Audit logs exported', 'success');
                } else {
                    this.showNotification('Failed to export audit logs', 'error');
                }
            } catch (error) {
                console.error('Error exporting audit logs:', error);
                this.showNotification('Failed to export audit logs', 'error');
            }
        },

        /**
         * View log details
         */
        viewLogDetails(log) {
            const details = JSON.stringify(log.details || {}, null, 2);
            alert(`Log Details:\n\n${details}`);
            // In production, this would show a modal with formatted details
        },

        /**
         * Get organization ID from URL or storage
         */
        getOrganizationId() {
            // Get from URL parameter or localStorage
            const params = new URLSearchParams(window.location.search);
            return params.get('org_id') || localStorage.getItem('currentOrgId') || '';
        },

        /**
         * Get request headers
         */
        getHeaders() {
            return {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`,
                'X-Organization-ID': this.getOrganizationId()
            };
        },

        /**
         * Get auth token
         */
        getAuthToken() {
            return localStorage.getItem('authToken') || '';
        },

        /**
         * Get quota CSS class
         */
        getQuotaClass(quota) {
            if (!quota.percentage) return 'quota-ok';
            if (quota.percentage >= 95) return 'quota-danger';
            if (quota.percentage >= 80) return 'quota-warning';
            return 'quota-ok';
        },

        /**
         * Get quota icon
         */
        getQuotaIcon(quota, name) {
            const icons = {
                'documents_per_month': 'fa-file-alt text-blue-600',
                'storage_gb': 'fa-hdd text-purple-600',
                'api_calls_per_day': 'fa-network-wired text-green-600',
                'users': 'fa-users text-orange-600',
                'teams': 'fa-user-friends text-pink-600',
                'ai_queries_per_month': 'fa-brain text-indigo-600'
            };
            return icons[name] || 'fa-info-circle text-gray-600';
        },

        /**
         * Get progress bar color
         */
        getProgressBarColor(quota) {
            if (!quota.percentage) return 'bg-green-500';
            if (quota.percentage >= 95) return 'bg-red-500';
            if (quota.percentage >= 80) return 'bg-yellow-500';
            return 'bg-green-500';
        },

        /**
         * Format quota name
         */
        formatQuotaName(name) {
            return name
                .replace(/_/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase())
                .replace('Per Month', '/month')
                .replace('Per Day', '/day')
                .replace('Gb', 'GB');
        },

        /**
         * Format feature name
         */
        formatFeatureName(name) {
            return name
                .replace(/_/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase());
        },

        /**
         * Format date
         */
        formatDate(dateString) {
            if (!dateString) return '-';
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        },

        /**
         * Format date and time
         */
        formatDateTime(dateString) {
            if (!dateString) return '-';
            const date = new Date(dateString);
            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        /**
         * Show notification
         */
        showNotification(message, type = 'info') {
            // Simple alert for now
            // In production, use a proper notification library
            if (type === 'error') {
                alert(`Error: ${message}`);
            } else {
                alert(message);
            }
        }
    };
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Alpine.js will automatically initialize the organizationDashboard component
    console.log('Organization dashboard loaded');
});
