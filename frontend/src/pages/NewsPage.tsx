import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from '@/lib/axios';
import { NewsPost, NewsCard } from '@/components/news/NewsCard';
import { Search, Loader2, Newspaper, AlertCircle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function NewsPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedTag, setSelectedTag] = useState<string | null>(null);

    const { data: news, isLoading, error } = useQuery<NewsPost[]>({
        queryKey: ['news', selectedTag],
        queryFn: async () => {
            const params: any = {};
            if (selectedTag) params.tag = selectedTag;
            const res = await axios.get('/news', { params });
            return res.data;
        }
    });

    const filteredNews = news?.filter(post =>
        post.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        post.excerpt?.toLowerCase().includes(searchTerm.toLowerCase())
    ) || [];

    const pinnedPost = filteredNews.find(p => p.is_pinned);
    const otherPosts = filteredNews.filter(p => p.id !== pinnedPost?.id);

    // Extract all unique tags
    const allTags = Array.from(new Set(news?.flatMap(p => p.tags || []) || [])).slice(0, 10);

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
                <p className="text-sm text-zinc-500 animate-pulse">Fetching latest updates and patch notes...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 max-w-md mx-auto text-center px-4">
                <AlertCircle className="w-12 h-12 text-red-400" />
                <h2 className="text-2xl font-bold text-white">Failed to load news</h2>
                <p className="text-sm text-zinc-400">Unable to retrieve announcements from the news service.</p>
                <Button onClick={() => window.location.reload()} className="bg-violet-600 hover:bg-violet-500 text-white">
                    Try Again
                </Button>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 pb-2">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
                        <Newspaper className="w-8 h-8 text-violet-400" />
                        News & Announcements
                    </h1>
                    <p className="text-zinc-400 mt-1 text-sm">
                        Patch notes, developer blogs, and platform releases.
                    </p>
                </div>

                <div className="relative w-full md:w-80">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                        placeholder="Search updates and notes..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-9 py-2 bg-zinc-900/80 border border-white/10 rounded-xl text-sm text-white placeholder-zinc-500 focus:border-violet-500 focus:outline-none transition-colors"
                    />
                    {searchTerm && (
                        <button
                            onClick={() => setSearchTerm("")}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white p-1"
                        >
                            <X className="w-3.5 h-3.5" />
                        </button>
                    )}
                </div>
            </div>

            {/* Tags Filter Strip */}
            {allTags.length > 0 && (
                <div className="flex flex-wrap gap-2 items-center">
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mr-1">Filter:</span>
                    <button
                        onClick={() => setSelectedTag(null)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                            selectedTag === null
                                ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                                : "bg-zinc-900/80 text-zinc-400 hover:text-white hover:bg-zinc-800 border border-white/10"
                        }`}
                    >
                        All Updates
                    </button>
                    {allTags.map(tag => (
                        <button
                            key={tag}
                            onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all capitalize ${
                                selectedTag === tag
                                    ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                                    : "bg-zinc-900/80 text-zinc-400 hover:text-white hover:bg-zinc-800 border border-white/10"
                            }`}
                        >
                            {tag}
                        </button>
                    ))}
                </div>
            )}

            {/* Featured/Pinned Post */}
            {pinnedPost && !searchTerm && !selectedTag && (
                <div className="pt-2">
                    <NewsCard post={pinnedPost} featured />
                </div>
            )}

            {/* Main Articles Grid */}
            {otherPosts.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-2">
                    {otherPosts.map((post) => (
                        <NewsCard key={post.id} post={post} />
                    ))}
                </div>
            ) : (
                <div className="text-center py-20 px-6 rounded-2xl bg-zinc-900/40 border border-white/5 space-y-3 max-w-md mx-auto">
                    <div className="w-14 h-14 rounded-2xl bg-zinc-800/80 border border-white/10 flex items-center justify-center mx-auto text-zinc-500">
                        <Newspaper className="w-7 h-7" />
                    </div>
                    <h3 className="text-lg font-bold text-white">
                        {searchTerm ? `No articles matching "${searchTerm}"` : "No announcements found"}
                    </h3>
                    <p className="text-xs text-zinc-400">
                        Check back later for newly published patch notes and development updates.
                    </p>
                    {(searchTerm || selectedTag) && (
                        <button
                            onClick={() => {
                                setSearchTerm("");
                                setSelectedTag(null);
                            }}
                            className="text-xs text-violet-400 hover:text-violet-300 underline font-medium"
                        >
                            Reset filters
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
