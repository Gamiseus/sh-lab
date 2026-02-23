import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from '@/lib/axios';
import { NewsPost, NewsCard } from '@/components/news/NewsCard';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Search, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function NewsPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedTag, setSelectedTag] = useState<string | null>(null);

    const { data: news, isLoading, error } = useQuery<NewsPost[]>({
        queryKey: ['news', selectedTag],
        queryFn: async () => {
            const params: any = {};
            if (selectedTag) params.tag = selectedTag;
            const res = await axios.get('/api/v1/news', { params });
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
    const allTags = Array.from(new Set(news?.flatMap(p => p.tags || []) || [])).slice(0, 8);

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <p className="text-muted-foreground animate-pulse">Fetching latest updates...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
                <AlertCircle className="w-12 h-12 text-destructive" />
                <h2 className="text-2xl font-bold">Failed to load news</h2>
                <p className="text-muted-foreground">Unable to connect to the news service.</p>
                <Button onClick={() => window.location.reload()}>Try Again</Button>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 max-w-7xl animate-in fade-in duration-500">

            {/* Header Section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
                <div>
                    <h1 className="text-4xl font-black flex items-center gap-3">
                        <Sparkles className="w-8 h-8 text-primary" />
                        What's New
                    </h1>
                    <p className="text-muted-foreground mt-2 text-lg">
                        Latest updates, patch notes, and community announcements.
                    </p>
                </div>

                <div className="flex flex-col items-end gap-4 w-full md:w-auto">
                    <div className="relative w-full md:w-80">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                            placeholder="Search updates..."
                            value={searchTerm}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
                            className="pl-9 bg-card/50 backdrop-blur-sm"
                        />
                    </div>
                </div>
            </div>

            {/* Tags Filter */}
            {allTags.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-8 items-center">
                    <span className="text-sm font-semibold text-muted-foreground mr-2">Filter by:</span>
                    <Badge
                        variant={selectedTag === null ? "default" : "outline"}
                        className="cursor-pointer hover:bg-primary/20 transition-colors"
                        onClick={() => setSelectedTag(null)}
                    >
                        All
                    </Badge>
                    {allTags.map(tag => (
                        <Badge
                            key={tag}
                            variant={selectedTag === tag ? "default" : "outline"}
                            className="cursor-pointer hover:bg-primary/20 transition-colors capitalize"
                            onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
                        >
                            {tag}
                        </Badge>
                    ))}
                </div>
            )}

            {/* Featured/Pinned Post */}
            {pinnedPost && !searchTerm && !selectedTag && (
                <div className="mb-12">
                    <NewsCard post={pinnedPost} featured />
                </div>
            )}

            {/* Main Grid */}
            {otherPosts.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {otherPosts.map((post) => (
                        <NewsCard key={post.id} post={post} />
                    ))}
                </div>
            ) : (
                <div className="text-center py-20 text-muted-foreground">
                    {searchTerm ? 'No posts matching your search.' : 'No news posts found.'}
                </div>
            )}
        </div>
    );
}
