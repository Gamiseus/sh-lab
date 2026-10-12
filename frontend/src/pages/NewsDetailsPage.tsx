import { useQuery } from '@tanstack/react-query';
import axios from '@/lib/axios';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Calendar, User, Clock, Loader2, AlertCircle, Share2, Sparkles } from 'lucide-react';
import { NewsPost } from '@/components/news/NewsCard';
import { getImageUrl } from '@/lib/api';
import { useState } from 'react';

export function NewsDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const postId = id;
    const [copied, setCopied] = useState(false);

    const { data: post, isLoading, error } = useQuery<NewsPost>({
        queryKey: ['news', postId],
        queryFn: async () => {
            const res = await axios.get(`/news/${postId}`);
            return res.data;
        },
        enabled: !!postId
    });

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
                <p className="text-sm text-zinc-500">Loading announcement...</p>
            </div>
        );
    }

    if (error || !post) {
        return (
            <div className="max-w-xl mx-auto py-20 px-6 text-center space-y-4">
                <AlertCircle className="w-14 h-14 text-red-400 mx-auto" />
                <h1 className="text-2xl font-bold text-white">Article not found</h1>
                <p className="text-sm text-zinc-400">The requested article could not be loaded or may have been unpinned.</p>
                <Link to="/news">
                    <button className="px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-semibold transition-colors mt-2">
                        Return to News
                    </button>
                </Link>
            </div>
        );
    }

    const date = new Date(post.published_at).toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    const readTime = Math.max(1, Math.ceil((post.content?.split(/\s+/).length || 100) / 200));
    const formattedContent = post.content?.replace(/\n/g, '  \n');

    const handleShare = () => {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(window.location.href);
            setCopied(true);
            setTimeout(() => setCopied(false), 2500);
        }
    };

    return (
        <div className="relative min-h-screen pb-20 animate-in fade-in duration-300">
            {/* Header Ambient Cover Backdrop */}
            {post.cover_image_url && (
                <div className="absolute inset-x-0 top-0 h-80 overflow-hidden z-0 pointer-events-none">
                    <img
                        src={getImageUrl(post.cover_image_url)}
                        alt=""
                        className="w-full h-full object-cover filter blur-3xl opacity-20 scale-110"
                    />
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/80 to-background" />
                </div>
            )}

            <div className="relative z-10 max-w-4xl mx-auto px-6 pt-6 space-y-8">
                {/* Navigation & Share Row */}
                <div className="flex items-center justify-between">
                    <Link
                        to="/news"
                        className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-white/10 text-xs font-semibold transition-colors"
                    >
                        <ArrowLeft className="w-4 h-4 text-violet-400" /> Back to News
                    </Link>

                    <button
                        onClick={handleShare}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-zinc-900/80 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-white/10 text-xs font-medium transition-colors"
                        title="Copy article link"
                    >
                        <Share2 className="w-3.5 h-3.5" />
                        <span>{copied ? "Link Copied!" : "Share"}</span>
                    </button>
                </div>

                {/* Article Header */}
                <header className="space-y-5 border-b border-white/10 pb-8">
                    <div className="flex items-center gap-2 flex-wrap">
                        {post.is_pinned && (
                            <Badge className="bg-violet-600 hover:bg-violet-500 text-white font-bold tracking-wide uppercase text-[11px] px-2.5 py-0.5 shadow-md flex items-center gap-1">
                                <Sparkles className="w-3 h-3 fill-current" />
                                Featured Update
                            </Badge>
                        )}
                        {post.tags?.map(tag => (
                            <Badge key={tag} variant="secondary" className="backdrop-blur-md bg-zinc-900/80 border border-white/10 text-zinc-300 text-xs capitalize">
                                {tag}
                            </Badge>
                        ))}
                    </div>

                    <h1 className="text-3xl sm:text-5xl font-black text-white leading-tight tracking-tight">
                        {post.title}
                    </h1>

                    {post.excerpt && (
                        <p className="text-base sm:text-lg text-zinc-300 leading-relaxed font-normal">
                            {post.excerpt}
                        </p>
                    )}

                    <div className="flex flex-wrap items-center gap-5 text-xs text-zinc-400 pt-2">
                        <div className="flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                            <span>{date}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5 text-zinc-500" />
                            <span>{readTime} min read</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <User className="w-3.5 h-3.5 text-zinc-500" />
                            <span>Published by <strong className="text-white font-semibold">{post.author_display_name || 'Admin'}</strong></span>
                        </div>
                    </div>
                </header>

                {/* Cover Image Feature (if present) */}
                {post.cover_image_url && (
                    <div className="rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
                        <img
                            src={getImageUrl(post.cover_image_url)}
                            alt={post.title}
                            className="w-full max-h-[480px] object-cover"
                        />
                    </div>
                )}

                {/* Article Body */}
                <article className="prose prose-invert prose-lg max-w-none prose-headings:text-white prose-headings:font-bold prose-p:text-zinc-300 prose-p:leading-relaxed prose-a:text-violet-400 hover:prose-a:text-violet-300 prose-strong:text-white prose-code:text-violet-300 prose-code:bg-zinc-900 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded">
                    {/* @ts-ignore */}
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkBreaks]}
                        components={{
                            img: ({ node, ...props }) => (
                                <img
                                    {...props}
                                    src={getImageUrl(props.src as string)}
                                    className="rounded-2xl shadow-xl my-8 w-full border border-white/10"
                                    loading="lazy"
                                />
                            )
                        }}
                    >
                        {/* @ts-ignore */}
                        {formattedContent}
                    </ReactMarkdown>
                </article>
            </div>
        </div>
    );
}
