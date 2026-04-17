
import { useQuery } from '@tanstack/react-query';
import axios from '@/lib/axios';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArrowLeft, Calendar, User, Clock, Loader2, AlertCircle } from 'lucide-react';
import { NewsPost } from '@/components/news/NewsCard';
import { getImageUrl } from '@/lib/api';

export function NewsDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const postId = id;

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
            <div className="flex flex-col items-center justify-center h-screen bg-background/50 backdrop-blur-sm fixed inset-0 z-50">
                <Loader2 className="w-10 h-10 animate-spin text-primary" />
            </div>
        );
    }

    if (error || !post) {
        return (
            <div className="container mx-auto p-12 text-center">
                <AlertCircle className="w-16 h-16 text-destructive mx-auto mb-4" />
                <h1 className="text-3xl font-bold mb-4">Article not found</h1>
                <Link to="/news">
                    <Button>Return to News</Button>
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

    // Calculate read time roughly
    // @ts-ignore
    const readTime = Math.ceil((post.content?.split(' ').length || 0) / 200);

    // Force hard breaks for newlines to match user expectation "Enter = Newline"
    // We add two spaces before every newline, which is standard Markdown for <br>
    const formattedContent = post.content?.replace(/\n/g, '  \n');

    return (
        <div className="min-h-screen bg-background relative">
            {/* Background with overlay */}
            <div className="absolute inset-0 z-0 h-[50vh] overflow-hidden">
                {post.cover_image_url && (
                    <img
                        src={getImageUrl(post.cover_image_url)}
                        alt={post.title}
                        className="w-full h-full object-cover opacity-30 blur-sm mask-image-gradient-b"
                    />
                )}
                <div className="absolute inset-0 bg-gradient-to-b from-transparent to-background" />
            </div>

            <ScrollArea className="h-screen pt-6 z-10 relative">
                <div className="container mx-auto px-4 max-w-4xl pb-20">

                    <Link to="/news" className="inline-block mb-8">
                        <Button variant="ghost" className="hover:bg-background/50 backdrop-blur-sm gap-2">
                            <ArrowLeft className="w-4 h-4" /> Back to News
                        </Button>
                    </Link>

                    <header className="mb-10 space-y-6">
                        <div className="flex items-center gap-2">
                            {post.is_pinned && (
                                <Badge className="bg-primary hover:bg-primary">Featured</Badge>
                            )}
                            {post.tags?.map(tag => (
                                <Badge key={tag} variant="secondary" className="backdrop-blur bg-background/50">{tag}</Badge>
                            ))}
                        </div>

                        <h1 className="text-4xl md:text-6xl font-black leading-tight tracking-tight">
                            {post.title}
                        </h1>

                        <div className="flex flex-wrap items-center gap-6 text-muted-foreground text-sm border-t border-b border-border/50 py-4">
                            <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                {date}
                            </div>
                            <div className="flex items-center gap-2">
                                <User className="w-4 h-4" />
                                {post.author_display_name || 'Admin'}
                            </div>
                            <div className="flex items-center gap-2">
                                <Clock className="w-4 h-4" />
                                {readTime} min read
                            </div>
                        </div>
                    </header>

                    <article className="prose prose-zinc dark:prose-invert prose-lg max-w-none">
                        {/* @ts-ignore */}
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm, remarkBreaks]}
                            components={{
                                img: ({ node, ...props }) => (
                                    <img
                                        {...props}
                                        src={getImageUrl(props.src as string)}
                                        className="rounded-xl shadow-lg my-8 w-full border border-border/50"
                                    />
                                )
                            }}
                        >
                            {/* @ts-ignore */}
                            {formattedContent}
                        </ReactMarkdown>
                    </article>
                </div>
            </ScrollArea>
        </div>
    );
}
