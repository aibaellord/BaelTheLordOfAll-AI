import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const login = useAuthStore((state) => state.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(email, password);
      toast.success('Welcome to BAEL!');
      navigate('/');
    } catch (error) {
      toast.error('Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md p-8 bg-white rounded-2xl shadow-2xl"
      >
        <div className="mb-8 text-center">
          <h1 className="mb-2 text-4xl font-bold text-indigo-600">BAEL</h1>
          <p className="text-gray-600">AI Agent Orchestration Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block mb-2 text-sm font-medium text-gray-700">Email</label>
            <div className="relative">
              <Mail className="absolute w-5 h-5 text-gray-400 left-3 top-3" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full py-2 pl-10 pr-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="admin@bael.ai"
                required
              />
            </div>
          </div>

          <div>
            <label className="block mb-2 text-sm font-medium text-gray-700">Password</label>
            <div className="relative">
              <Lock className="absolute w-5 h-5 text-gray-400 left-3 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full py-2 pl-10 pr-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center justify-center w-full px-4 py-3 font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <p className="mt-6 text-sm text-center text-gray-600">
          Demo credentials: any email + password
        </p>
      </motion.div>
    </div>
  );
}
