revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('domain', sa.String(), nullable=False, unique=True),
        sa.Column('ip', sa.String(), nullable=False, unique=True),
        sa.Column('public_key', sa.String(), nullable=False),
        sa.Column('private_key', sa.String(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_table(
        'github_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('pat_token', sa.String(), nullable=False),
        sa.Column('repo_name', sa.String(), nullable=False),
        sa.Column('target_runners', sa.Integer(), default=20),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_dispatched_at', sa.DateTime(), nullable=True)
    )
    op.create_table(
        'runners',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('github_accounts.id'), nullable=True),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.Column('mesh_ip', sa.String(), nullable=False),
        sa.Column('tun_name', sa.String(), nullable=False),
        sa.Column('tun_client_ip', sa.String(), nullable=False),
        sa.Column('tun_server_ip', sa.String(), nullable=False),
        sa.Column('pubkey', sa.String(), nullable=False),
        sa.Column('egress_ip', sa.String(), nullable=True),
        sa.Column('healthy', sa.Boolean(), default=False),
        sa.Column('ping_ms', sa.Float(), default=0.0),
        sa.Column('last_seen', sa.DateTime(), nullable=True)
    )
    op.create_table(
        'ssh_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('public_key', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_table(
        'dns_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('domain', sa.String(), nullable=False, unique=True),
        sa.Column('ip', sa.String(), nullable=False)
    )

def downgrade():
    op.drop_table('dns_records')
    op.drop_table('ssh_keys')
    op.drop_table('runners')
    op.drop_table('github_accounts')
    op.drop_table('clients')
