import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    domain = Column(String, unique=True, index=True, nullable=False)
    ip = Column(String, unique=True, index=True, nullable=False)
    public_key = Column(String, nullable=False)
    private_key = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class GitHubAccount(Base):
    __tablename__ = "github_accounts"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    pat_token = Column(String, nullable=False)
    repo_name = Column(String, nullable=False)
    target_runners = Column(Integer, default=20)
    is_active = Column(Boolean, default=True)
    last_dispatched_at = Column(DateTime, nullable=True)

class Runner(Base):
    __tablename__ = "runners"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("github_accounts.id"), nullable=True)
    node_id = Column(Integer, nullable=False)
    mesh_ip = Column(String, nullable=False)
    tun_name = Column(String, nullable=False)
    tun_client_ip = Column(String, nullable=False)
    tun_server_ip = Column(String, nullable=False)
    pubkey = Column(String, nullable=False)
    egress_ip = Column(String, nullable=True)
    healthy = Column(Boolean, default=False)
    ping_ms = Column(Float, default=0.0)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)

class SSHKey(Base):
    __tablename__ = "ssh_keys"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    public_key = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class DNSRecord(Base):
    __tablename__ = "dns_records"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, nullable=False)
    ip = Column(String, nullable=False)
