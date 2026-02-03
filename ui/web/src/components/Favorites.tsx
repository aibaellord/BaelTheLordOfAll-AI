import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Star, X, ChevronRight, MessageSquare, Zap, Brain, Database, Terminal, GitBranch } from 'lucide-react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useNavigate } from 'react-router-dom';

// Favorite item type
interface FavoriteItem {
  id: string;
  type: 'page' | 'chat' | 'workflow' | 'memory' | 'command';
  title: string;
  path?: string;
  action?: string;
  icon?: string;
  addedAt: number;
}

interface FavoritesStore {
  favorites: FavoriteItem[];
  addFavorite: (item: Omit<FavoriteItem, 'id' | 'addedAt'>) => void;
  removeFavorite: (id: string) => void;
  isFavorite: (path: string) => boolean;
  reorderFavorites: (startIndex: number, endIndex: number) => void;
}

// Icons mapping
const iconMap: Record<string, React.ElementType> = {
  'message-square': MessageSquare,
  'zap': Zap,
  'brain': Brain,
  'database': Database,
  'terminal': Terminal,
  'git-branch': GitBranch,
};

export const useFavoritesStore = create<FavoritesStore>()(
  persist(
    (set, get) => ({
      favorites: [],

      addFavorite: (item) => {
        const id = `fav-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        set((state) => ({
          favorites: [...state.favorites, { ...item, id, addedAt: Date.now() }].slice(0, 20) // Max 20 favorites
        }));
      },

      removeFavorite: (id) => {
        set((state) => ({
          favorites: state.favorites.filter(f => f.id !== id)
        }));
      },

      isFavorite: (path) => {
        return get().favorites.some(f => f.path === path);
      },

      reorderFavorites: (startIndex, endIndex) => {
        set((state) => {
          const result = Array.from(state.favorites);
          const [removed] = result.splice(startIndex, 1);
          result.splice(endIndex, 0, removed);
          return { favorites: result };
        });
      },
    }),
    {
      name: 'bael-favorites',
    }
  )
);

// Favorite toggle button for pages
export function FavoriteButton({
  path,
  title,
  type = 'page',
  icon
}: {
  path: string;
  title: string;
  type?: FavoriteItem['type'];
  icon?: string;
}) {
  const { favorites, addFavorite, removeFavorite, isFavorite } = useFavoritesStore();
  const isFav = isFavorite(path);

  const handleToggle = () => {
    if (isFav) {
      const fav = favorites.find(f => f.path === path);
      if (fav) removeFavorite(fav.id);
    } else {
      addFavorite({ type, title, path, icon });
    }
  };

  return (
    <motion.button
      onClick={handleToggle}
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.9 }}
      className={`p-1.5 rounded-lg transition-colors ${
        isFav
          ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-400/10'
          : 'text-bael-muted hover:text-bael-text hover:bg-bael-border'
      }`}
      title={isFav ? 'Remove from favorites' : 'Add to favorites'}
    >
      <Star className={`w-4 h-4 ${isFav ? 'fill-amber-400' : ''}`} />
    </motion.button>
  );
}

// Favorites sidebar section
export function FavoritesSidebar() {
  const { favorites, removeFavorite } = useFavoritesStore();
  const navigate = useNavigate();

  if (favorites.length === 0) return null;

  return (
    <div className="px-2 mb-4">
      <div className="flex items-center justify-between px-2 py-1.5 text-xs uppercase tracking-wide text-bael-muted">
        <span className="flex items-center gap-1">
          <Star className="w-3 h-3 text-amber-400" />
          Favorites
        </span>
      </div>
      <ul className="space-y-0.5">
        {favorites.slice(0, 8).map((fav) => {
          const Icon = fav.icon ? iconMap[fav.icon] || Star : Star;
          return (
            <li key={fav.id}>
              <div className="flex items-center group">
                <button
                  onClick={() => fav.path && navigate(fav.path)}
                  className="flex-1 flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-bael-muted hover:text-bael-text hover:bg-bael-border/50 transition-colors text-left truncate"
                >
                  <Icon className="w-4 h-4 text-amber-400/70" />
                  <span className="truncate">{fav.title}</span>
                </button>
                <button
                  onClick={() => removeFavorite(fav.id)}
                  className="p-1 text-bael-muted hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Remove"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// Quick access bar (can be added to header)
export function FavoritesBar() {
  const { favorites } = useFavoritesStore();
  const navigate = useNavigate();

  if (favorites.length === 0) return null;

  return (
    <div className="hidden md:flex items-center gap-1 px-2">
      {favorites.slice(0, 5).map((fav) => {
        const Icon = fav.icon ? iconMap[fav.icon] || Star : Star;
        return (
          <motion.button
            key={fav.id}
            onClick={() => fav.path && navigate(fav.path)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs text-bael-muted hover:text-bael-text hover:bg-bael-border/50 transition-colors"
            title={fav.title}
          >
            <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
            <span className="max-w-[60px] truncate">{fav.title}</span>
          </motion.button>
        );
      })}
    </div>
  );
}

export default FavoritesSidebar;
