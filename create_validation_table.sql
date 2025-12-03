CREATE TABLE IF NOT EXISTS cluster_validation_metrics (
    id BIGSERIAL PRIMARY KEY,
    clustering_job_id INTEGER REFERENCES clustering_jobs(id) ON DELETE CASCADE,
    clustering_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    num_clusters INTEGER NOT NULL CHECK (num_clusters >= 2),
    total_accidents INTEGER NOT NULL CHECK (total_accidents >= 1),
    silhouette_score DOUBLE PRECISION CHECK (silhouette_score >= -1.0 AND silhouette_score <= 1.0),
    davies_bouldin_index DOUBLE PRECISION CHECK (davies_bouldin_index >= 0.0),
    calinski_harabasz_score DOUBLE PRECISION CHECK (calinski_harabasz_score >= 0.0),
    cluster_quality VARCHAR(20) NOT NULL DEFAULT '',
    linkage_method VARCHAR(20) NOT NULL DEFAULT 'complete',
    distance_threshold DOUBLE PRECISION NOT NULL,
    CONSTRAINT unique_clustering_job UNIQUE (clustering_job_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_validation_metrics_date ON cluster_validation_metrics(clustering_date DESC);
