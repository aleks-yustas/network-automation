CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS netops_devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL UNIQUE,
    vendor text NOT NULL,
    model text NOT NULL,
    host text,
    mgmt_ip inet NOT NULL,
    site text,
    region text,
    enabled boolean NOT NULL DEFAULT true,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS netops_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type text NOT NULL,
    device_id uuid REFERENCES netops_devices(id) ON DELETE SET NULL,
    scenario text NOT NULL,
    transport text NOT NULL,
    status text NOT NULL CHECK (status IN ('NEW', 'RUNNING', 'DONE', 'FAILED', 'RETRY', 'SKIPPED', 'TIMEOUT')),
    priority integer NOT NULL DEFAULT 100,
    attempt integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 3,
    run_after timestamptz NOT NULL DEFAULT now(),
    locked_by text,
    locked_at timestamptz,
    timeout_sec integer NOT NULL DEFAULT 300,
    expires_at timestamptz,
    idempotency_key text UNIQUE,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    result jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_code text,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_netops_jobs_ready
    ON netops_jobs (priority DESC, run_after ASC, created_at ASC)
    WHERE status IN ('NEW', 'RETRY');

CREATE INDEX IF NOT EXISTS idx_netops_jobs_expires_at
    ON netops_jobs (expires_at)
    WHERE status IN ('NEW', 'RETRY', 'RUNNING');

CREATE INDEX IF NOT EXISTS idx_netops_jobs_running_timeout
    ON netops_jobs (locked_at)
    WHERE status = 'RUNNING';

CREATE TABLE IF NOT EXISTS netops_job_events (
    id bigserial PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES netops_jobs(id) ON DELETE CASCADE,
    status text NOT NULL,
    message text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_netops_job_events_job_id_created_at
    ON netops_job_events (job_id, created_at);

CREATE TABLE IF NOT EXISTS netops_artifacts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL REFERENCES netops_jobs(id) ON DELETE CASCADE,
    device_id uuid REFERENCES netops_devices(id) ON DELETE SET NULL,
    artifact_type text NOT NULL,
    path text NOT NULL,
    checksum_sha256 text,
    size_bytes bigint,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_netops_artifacts_device_created
    ON netops_artifacts (device_id, created_at DESC);

CREATE TABLE IF NOT EXISTS netops_device_credentials (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid NOT NULL REFERENCES netops_devices(id) ON DELETE CASCADE,
    purpose text NOT NULL,
    username text NOT NULL,
    secret jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (device_id, purpose)
);
