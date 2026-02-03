import React from 'react';
import { motion } from 'framer-motion';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circle' | 'rect' | 'card';
  width?: string | number;
  height?: string | number;
  count?: number;
}

// Base skeleton with shimmer animation
export function Skeleton({
  className = '',
  variant = 'rect',
  width,
  height,
  count = 1
}: SkeletonProps) {
  const baseClasses = 'animate-pulse bg-gradient-to-r from-bael-border via-bael-surface to-bael-border bg-[length:200%_100%]';

  const variantClasses = {
    text: 'h-4 rounded',
    circle: 'rounded-full',
    rect: 'rounded-lg',
    card: 'rounded-xl'
  };

  const style = {
    width: width ? (typeof width === 'number' ? `${width}px` : width) : undefined,
    height: height ? (typeof height === 'number' ? `${height}px` : height) : undefined,
  };

  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`${baseClasses} ${variantClasses[variant]} ${className}`}
          style={style}
        />
      ))}
    </>
  );
}

// Dashboard Card Skeleton
export function CardSkeleton() {
  return (
    <div className="bg-bael-surface border border-bael-border rounded-xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton variant="circle" width={40} height={40} />
        <Skeleton variant="text" width={60} />
      </div>
      <div className="space-y-2">
        <Skeleton variant="text" width="70%" />
        <Skeleton variant="text" width="40%" height={28} />
      </div>
    </div>
  );
}

// Stats Grid Skeleton
export function StatsGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

// Table Row Skeleton
export function TableRowSkeleton({ columns = 4 }: { columns?: number }) {
  return (
    <div className="flex items-center gap-4 p-4 border-b border-bael-border">
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          className="flex-1"
          height={16}
        />
      ))}
    </div>
  );
}

// Table Skeleton
export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="bg-bael-surface border border-bael-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-4 p-4 bg-bael-bg border-b border-bael-border">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} variant="text" className="flex-1" height={12} />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <TableRowSkeleton key={i} columns={columns} />
      ))}
    </div>
  );
}

// Chat Message Skeleton
export function ChatMessageSkeleton({ isUser = false }: { isUser?: boolean }) {
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <Skeleton variant="circle" width={36} height={36} />
      <div className={`space-y-2 ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <Skeleton variant="rect" width={200} height={16} />
        <Skeleton variant="rect" width={280} height={16} />
        <Skeleton variant="rect" width={160} height={16} />
      </div>
    </div>
  );
}

// Memory Card Skeleton
export function MemoryCardSkeleton() {
  return (
    <div className="bg-bael-surface border border-bael-border rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton variant="circle" width={24} height={24} />
          <Skeleton variant="text" width={100} />
        </div>
        <Skeleton variant="text" width={60} />
      </div>
      <Skeleton variant="text" className="w-full" />
      <Skeleton variant="text" width="80%" />
      <div className="flex gap-2 pt-2">
        <Skeleton variant="rect" width={60} height={24} className="rounded-full" />
        <Skeleton variant="rect" width={80} height={24} className="rounded-full" />
      </div>
    </div>
  );
}

// Agent Card Skeleton
export function AgentCardSkeleton() {
  return (
    <div className="bg-bael-surface border border-bael-border rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton variant="circle" width={48} height={48} />
        <div className="space-y-2 flex-1">
          <Skeleton variant="text" width="60%" height={20} />
          <Skeleton variant="text" width="40%" height={14} />
        </div>
      </div>
      <div className="flex gap-2">
        <Skeleton variant="rect" width="100%" height={32} />
        <Skeleton variant="rect" width={80} height={32} />
      </div>
    </div>
  );
}

// Full Page Loading Skeleton
export function PageLoadingSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton variant="text" width={200} height={28} />
          <Skeleton variant="text" width={300} height={16} />
        </div>
        <Skeleton variant="rect" width={120} height={40} />
      </div>

      {/* Stats */}
      <StatsGridSkeleton />

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TableSkeleton rows={6} columns={5} />
        </div>
        <div className="space-y-4">
          <MemoryCardSkeleton />
          <MemoryCardSkeleton />
          <MemoryCardSkeleton />
        </div>
      </div>
    </motion.div>
  );
}

// Council Member Skeleton
export function CouncilMemberSkeleton() {
  return (
    <div className="bg-bael-surface border border-bael-border rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton variant="circle" width={40} height={40} />
        <div className="space-y-1.5 flex-1">
          <Skeleton variant="text" width={120} height={18} />
          <Skeleton variant="text" width={80} height={14} />
        </div>
        <Skeleton variant="rect" width={60} height={24} className="rounded-full" />
      </div>
    </div>
  );
}

// Inline Loading Spinner
export function InlineSpinner({ size = 16, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      className={`animate-spin text-bael-primary ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export default Skeleton;
