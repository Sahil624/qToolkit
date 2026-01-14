import React, { useState, useEffect, useRef } from 'react';
import { refreshIcon, closeIcon } from '@jupyterlab/ui-components';
import { makeApiRequest } from './handler';

async function reindexVectorDB(): Promise<void> {
  return makeApiRequest<void>('vector_db', {
    operation: 'reindex'
  })
}

// --- Interfaces for Info Panel ---
interface TrackingData {
  completed_lessons: Record<string, boolean>;
  completed_learning_objects: Record<string, boolean>;
}

interface LoDetails {
  summary: string;
}

interface Manifest {
  course_chronology: string[];
  topics_included_count: number;
  lo_details: Record<string, LoDetails>;
}

interface CourseInfoResponse {
  max_course_progress: number;
  tracking_data: TrackingData;
  manifest: Manifest;
}

// --- Info Dialog Component ---
export interface InfoDialogProps {
  isOpen: boolean;
  onClose: () => void;
  currentLOid: string | null;
}

async function fetchCourseProgress(): Promise<CourseInfoResponse> {
  return makeApiRequest<CourseInfoResponse>('track_course', null, {
    method: 'GET'
  });
}

export const InfoDialog: React.FC<InfoDialogProps> = ({ isOpen, onClose, currentLOid }) => {
  const [data, setData] = useState<CourseInfoResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetchCourseProgress();
      setData(res);
    } catch (e) {
      console.error("Failed to load course info", e);
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    try {
      await reindexVectorDB();
      alert("Vector DB reindexed successfully.");
    } catch (e) {
      alert("Failed to reindex Vector DB.");
    } finally {
      setReindexing(false);
    }
  };

  if (!isOpen) return null;

  // Calculate Progress
  const totalItems = data?.manifest.course_chronology.length || 0;
  const completedCount = data ? Object.keys(data.tracking_data.completed_learning_objects).length : 0;
  const progressPercent = totalItems > 0 ? Math.round((completedCount / totalItems) * 100) : 0;

  return (
    <div className="info-dialog-overlay">
      <div className="info-dialog">
        <div className="info-header">
          <span>Course Status</span>
          <button className="close-btn" onClick={onClose}>
            <closeIcon.react tag="span" />
          </button>
        </div>

        <div className="info-content">
          {loading ? (
            <div className="loading-spinner">Loading course data...</div>
          ) : data ? (
            <>
              {/* 1. Course Completion Info */}
              <div className="info-section">
                <h3>Progress</h3>
                <div className="progress-bar-container">
                  <div className="progress-bar" style={{ width: `${progressPercent}%` }}></div>
                </div>
                <div className="progress-text">
                  {completedCount} / {totalItems} modules completed ({progressPercent}%)
                </div>
              </div>

              {/* 3. Roadmap View */}
              <div className="info-section roadmap-section">
                <h3>Roadmap</h3>
                <ul className="roadmap-list">
                  {data.manifest.course_chronology.map((loId, idx) => {
                    const isCompleted = data.tracking_data.completed_learning_objects[loId];
                    const isCurrent = loId === currentLOid;

                    let statusClass = "future";
                    if (isCompleted) statusClass = "completed";
                    if (isCurrent) statusClass = "current";

                    return (
                      <li key={loId} className={`roadmap-item ${statusClass}`}>
                        <div className="status-dot"></div>
                        <a href={`/voila/render/generated_course/${loId}/${loId}.ipynb`}>
                          <span className="lo-id">{loId} - {data.manifest.lo_details[loId]?.summary}</span>
                        </a>
                        {isCurrent && <span className="current-badge">Current</span>}
                        {isCompleted && <span className="check-mark">✓</span>}
                      </li>
                    );
                  })}
                </ul>
              </div>

              {/* 2. Reindex Button */}
              <div className="info-section danger-zone">
                <h3>System</h3>
                <button
                  className="jp-mod-styled jp-mod-warn reindex-btn"
                  onClick={handleReindex}
                  disabled={reindexing}
                >
                  <refreshIcon.react tag="span" />
                  {reindexing ? " Reindexing..." : " Reindex Vector DB"}
                </button>
              </div>
            </>
          ) : (
            <div className="error-msg">Could not load course data.</div>
          )}
        </div>
      </div>
    </div>
  );
};