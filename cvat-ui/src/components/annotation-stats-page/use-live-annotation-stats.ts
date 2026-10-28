// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import { useEffect, useRef, useState } from 'react';

import { getCore } from 'cvat-core-wrapper';
import { AnnotationStats } from './annotation-stats-page';

const core = getCore();

export type LiveStatus = 'connecting' | 'live' | 'reconnecting' | 'stopped';

const INITIAL_RETRY_DELAY_MS = 1000;
const MAX_RETRY_DELAY_MS = 30000;
// the server closes with 4000 + HTTP status when it refuses the request (no login, no access, no task);
// reconnecting would be refused again
const REFUSED_CLOSE_CODES = { min: 4400, max: 4499 };

function socketURL(taskId: number, groupByType: boolean): string {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const query = groupByType ? '?group_by=type' : '';
    return `${protocol}://${window.location.host}${core.config.backendAPI}/tasks/${taskId}/annotation-stats/ws${query}`;
}

/**
 * Keeps a WebSocket open while `enabled` and calls `onStats` with every snapshot the server pushes.
 * A dropped connection is retried with exponential backoff; the server sends a full snapshot on
 * every (re)connect, so nothing missed while offline needs replaying.
 */
export function useLiveAnnotationStats(
    taskId: number,
    groupByType: boolean,
    enabled: boolean,
    onStats: (stats: AnnotationStats) => void,
): LiveStatus {
    const [status, setStatus] = useState<LiveStatus>('connecting');
    const onStatsRef = useRef(onStats);
    onStatsRef.current = onStats;

    useEffect(() => {
        if (!enabled) {
            return () => {};
        }

        let socket: WebSocket | null = null;
        let retryTimeout: ReturnType<typeof setTimeout> | null = null;
        let retryDelay = INITIAL_RETRY_DELAY_MS;
        let disposed = false;

        function connect(): void {
            socket = new WebSocket(socketURL(taskId, groupByType));

            socket.onmessage = (event: MessageEvent<string>) => {
                retryDelay = INITIAL_RETRY_DELAY_MS;
                setStatus('live');
                onStatsRef.current(JSON.parse(event.data));
            };

            socket.onclose = (event: CloseEvent) => {
                if (disposed) {
                    return;
                }

                if (event.code >= REFUSED_CLOSE_CODES.min && event.code <= REFUSED_CLOSE_CODES.max) {
                    setStatus('stopped');
                    return;
                }

                setStatus('reconnecting');
                retryTimeout = setTimeout(connect, retryDelay);
                retryDelay = Math.min(retryDelay * 2, MAX_RETRY_DELAY_MS);
            };
        }

        setStatus('connecting');
        connect();

        return () => {
            disposed = true;
            if (retryTimeout) {
                clearTimeout(retryTimeout);
            }
            socket?.close();
        };
    }, [taskId, groupByType, enabled]);

    return status;
}
