"""
Analytics Dashboard Module - Chart generation using Matplotlib
Generates charts for the Insights View in the Knowledge Graph
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import json
from datetime import datetime, timedelta
from collections import Counter
import os
import io
import base64

# Set style for dark theme
plt.style.use('dark_background')


class AnalyticsEngine:
    """Generates analytics charts and metrics from knowledge graph data"""
    
    def __init__(self, graph_data=None):
        self.graph_data = graph_data or {}
        self.colors = {
            'tweet': '#3498db',
            'action': '#e94560',
            'topic': '#00d9ff',
            'user': '#9b59b6',
            'grok': '#00ff88',
            'ai': '#8b5cf6',
            'x': '#1DA1F2'
        }
    
    def set_data(self, graph_data):
        """Set the data source for analytics"""
        self.graph_data = graph_data
    
    def get_stats(self):
        """Generate all statistics as JSON"""
        stats = {
            'overview': self._get_overview_stats(),
            'activity_over_time': self._get_activity_stats(),
            'topic_distribution': self._get_topic_stats(),
            'action_completion': self._get_action_stats(),
            'source_breakdown': self._get_source_stats(),
            'top_keywords': self._get_keyword_stats(),
            'engagement_trends': self._get_engagement_stats()
        }
        return stats
    
    def _get_overview_stats(self):
        """Get basic overview statistics"""
        graph = self.graph_data.get('graph', {})
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])
        actions = self.graph_data.get('actions', [])
        topics = self.graph_data.get('topics', {})
        conversations = self.graph_data.get('grok_conversations', [])
        ai_conversations = self.graph_data.get('ai_conversations', [])
        
        return {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'total_actions': len(actions),
            'total_topics': len(topics),
            'total_conversations': len(conversations) + len(ai_conversations),
            'action_completion_rate': self._calculate_completion_rate(actions)
        }
    
    def _calculate_completion_rate(self, actions):
        """Calculate percentage of completed actions"""
        if not actions:
            return 0
        completed = sum(1 for a in actions if a.get('status') == 'done')
        return round((completed / len(actions)) * 100, 1)
    
    def _get_activity_stats(self):
        """Get activity over time statistics"""
        nodes = self.graph_data.get('graph', {}).get('nodes', [])
        activities = []
        
        for node in nodes:
            date_str = node.get('date') or node.get('timestamp')
            if date_str:
                try:
                    if isinstance(date_str, str):
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date = datetime.fromtimestamp(date_str / 1000)
                    activities.append(date)
                except (ValueError, TypeError):
                    pass
        
        if not activities:
            return {'dates': [], 'counts': []}
        
        # Group by date
        activity_by_date = Counter(a.date() for a in activities)
        min_date = min(activity_by_date.keys())
        max_date = max(activity_by_date.keys())
        
        dates = []
        counts = []
        current = min_date
        while current <= max_date:
            dates.append(current.isoformat())
            counts.append(activity_by_date.get(current, 0))
            current += timedelta(days=1)
        
        return {'dates': dates, 'counts': counts}
    
    def _get_topic_stats(self):
        """Get topic distribution statistics"""
        topics = self.graph_data.get('topics', {})
        
        if not topics:
            return {'labels': [], 'values': []}
        
        # Sort topics by count and get top 10
        sorted_topics = sorted(topics.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        
        labels = [t[0] for t in sorted_topics]
        values = [len(t[1]) for t in sorted_topics]
        
        return {'labels': labels, 'values': values}
    
    def _get_action_stats(self):
        """Get action completion statistics by priority"""
        actions = self.graph_data.get('actions', [])
        
        if not actions:
            return {'urgent': {}, 'high': {}, 'medium': {}, 'low': {}}
        
        priorities = ['urgent', 'high', 'medium', 'low']
        stats = {}
        
        for priority in priorities:
            priority_actions = [a for a in actions if a.get('priority', 'medium') == priority]
            total = len(priority_actions)
            completed = sum(1 for a in priority_actions if a.get('status') == 'done')
            in_progress = sum(1 for a in priority_actions if a.get('status') == 'in_progress')
            pending = total - completed - in_progress
            
            stats[priority] = {
                'total': total,
                'completed': completed,
                'in_progress': in_progress,
                'pending': pending,
                'completion_rate': round((completed / total * 100), 1) if total > 0 else 0
            }
        
        return stats
    
    def _get_source_stats(self):
        """Get source breakdown (X, Grok, AI)"""
        nodes = self.graph_data.get('graph', {}).get('nodes', [])
        
        source_counts = {'x': 0, 'grok': 0, 'ai': 0}
        
        for node in nodes:
            source = node.get('source', '').lower()
            if 'grok' in source:
                source_counts['grok'] += 1
            elif 'ai' in source or 'chatgpt' in source or 'claude' in source or 'gemini' in source:
                source_counts['ai'] += 1
            elif 'x' in source or 'twitter' in source:
                source_counts['x'] += 1
        
        return source_counts
    
    def _get_keyword_stats(self):
        """Get top keywords from topics and content"""
        topics = self.graph_data.get('topics', {})
        nodes = self.graph_data.get('graph', {}).get('nodes', [])
        
        keywords = Counter()
        
        # Extract from topic names
        for topic in topics.keys():
            words = topic.lower().split()
            for word in words:
                if len(word) > 2:
                    keywords[word] += len(topics[topic])
        
        # Extract from node labels/text
        for node in nodes:
            text = node.get('label', '') or node.get('text', '') or ''
            words = text.lower().split()
            for word in words:
                if len(word) > 2 and word.isalpha():
                    keywords[word] += 1
        
        top_keywords = keywords.most_common(15)
        
        return {
            'keywords': [{'word': k[0], 'count': k[1]} for k in top_keywords]
        }
    
    def _get_engagement_stats(self):
        """Get engagement trends (monthly comparison)"""
        nodes = self.graph_data.get('graph', {}).get('nodes', [])
        
        monthly_data = {}
        
        for node in nodes:
            date_str = node.get('date') or node.get('timestamp')
            if date_str:
                try:
                    if isinstance(date_str, str):
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date = datetime.fromtimestamp(date_str / 1000)
                    month_key = date.strftime('%Y-%m')
                    monthly_data[month_key] = monthly_data.get(month_key, 0) + 1
                except (ValueError, TypeError):
                    pass
        
        sorted_months = sorted(monthly_data.items())
        
        return {
            'months': [m[0] for m in sorted_months],
            'counts': [m[1] for m in sorted_months]
        }
    
    # ==================== CHART GENERATION ====================
    
    def generate_activity_chart(self, output_path=None):
        """Generate activity over time line chart"""
        data = self._get_activity_stats()
        
        if not data['dates']:
            return self._create_empty_chart("No Activity Data")
        
        dates = [datetime.fromisoformat(d) for d in data['dates']]
        counts = data['counts']
        
        fig, ax = plt.subplots(figsize=(12, 5))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        
        ax.plot(dates, counts, color=self.colors['tweet'], linewidth=2, marker='o', markersize=4)
        ax.fill_between(dates, counts, alpha=0.3, color=self.colors['tweet'])
        
        ax.set_title('Activity Over Time', fontsize=14, color='#eee', pad=15)
        ax.set_xlabel('Date', fontsize=11, color='#888')
        ax.set_ylabel('Activity Count', fontsize=11, color='#888')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        plt.xticks(rotation=45, color='#888')
        plt.yticks(color='#888')
        
        ax.grid(True, alpha=0.2, color='#444')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#444')
        ax.spines['left'].set_color('#444')
        
        plt.tight_layout()
        
        return self._save_chart(fig, output_path)
    
    def generate_topic_chart(self, output_path=None):
        """Generate topic distribution pie chart"""
        data = self._get_topic_stats()
        
        if not data['labels']:
            return self._create_empty_chart("No Topics")
        
        labels = data['labels']
        values = data['values']
        
        # Custom colors for pie chart
        pie_colors = ['#00d9ff', '#00ff88', '#3498db', '#e94560', '#9b59b6', 
                      '#ffc107', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899']
        
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        
        wedges, texts, autotexts = ax.pie(
            values, 
            labels=labels,
            autopct=lambda pct: f'{pct:.1f}%' if pct > 0 else '',
            colors=pie_colors[:len(values)],
            startangle=90,
            explode=[0.02] * len(values)
        )
        
        for text in texts:
            text.set_color('#eee')
        for autotext in autotexts:
            autotext.set_color('#1a1a2e')
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
        
        ax.set_title('Topic Distribution (Top 10)', fontsize=14, color='#eee', pad=20)
        
        plt.tight_layout()
        
        return self._save_chart(fig, output_path)
    
    def generate_action_completion_chart(self, output_path=None):
        """Generate action completion progress bars by priority"""
        data = self._get_action_stats()
        
        priorities = ['urgent', 'high', 'medium', 'low']
        colors = {'urgent': '#e94560', 'high': '#ffc107', 'medium': '#00d9ff', 'low': '#00ff88'}
        
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        
        bar_height = 0.6
        y_positions = range(len(priorities))
        
        max_total = max((p.get('total', 0) for p in data.values()), default=1)
        
        for i, priority in enumerate(priorities):
            p = data.get(priority, {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0})
            total = p['total']
            
            # Stacked bar
            completed_width = (p['completed'] / max_total) * 100
            in_progress_width = (p['in_progress'] / max_total) * 100
            pending_width = (p['pending'] / max_total) * 100
            
            # Draw bars
            ax.barh(i, completed_width, bar_height, color='#00ff88', label='Completed' if i == 0 else '')
            ax.barh(i, in_progress_width, bar_height, left=completed_width, color='#ffc107', label='In Progress' if i == 0 else '')
            ax.barh(i, pending_width, bar_height, left=completed_width + in_progress_width, color='#444', label='Pending' if i == 0 else '')
            
            # Add text labels
            completion_rate = p['completion_rate']
            ax.text(102, i, f'{completion_rate:.0f}% ({p["completed"]}/{total})', 
                   va='center', fontsize=10, color='#888')
        
        ax.set_yticks(y_positions)
        ax.set_yticklabels([p.capitalize() for p in priorities], color='#eee')
        ax.set_xlabel('Percentage', fontsize=11, color='#888')
        ax.set_title('Action Completion by Priority', fontsize=14, color='#eee', pad=15)
        
        ax.set_xlim(0, 120)
        ax.legend(loc='lower right', fontsize=9, facecolor='#1a1a2e', edgecolor='#444')
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#444')
        ax.spines['left'].set_color('#444')
        
        plt.tight_layout()
        
        return self._save_chart(fig, output_path)
    
    def generate_source_breakdown_chart(self, output_path=None):
        """Generate source breakdown bar chart (X vs Grok vs AI)"""
        data = self._get_source_stats()
        
        sources = ['X', 'Grok', 'AI']
        values = [data['x'], data['grok'], data['ai']]
        colors = [self.colors['x'], self.colors['grok'], self.colors['ai']]
        
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        
        bars = ax.bar(sources, values, color=colors, edgecolor='#1a1a2e', linewidth=2)
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.02,
                   str(val), ha='center', va='bottom', fontsize=12, fontweight='bold', color='#eee')
        
        ax.set_ylabel('Count', fontsize=11, color='#888')
        ax.set_title('Source Breakdown', fontsize=14, color='#eee', pad=15)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#444')
        ax.spines['left'].set_color('#444')
        
        plt.yticks(color='#888')
        plt.xticks(color='#eee', fontsize=11)
        
        plt.tight_layout()
        
        return self._save_chart(fig, output_path)
    
    def generate_keywords_chart(self, output_path=None):
        """Generate top keywords horizontal bar chart"""
        data = self._get_keyword_stats()
        
        keywords = data.get('keywords', [])[:15]
        
        if not keywords:
            return self._create_empty_chart("No Keywords")
        
        words = [k['word'] for k in keywords]
        counts = [k['count'] for k in keywords]
        
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        
        y_positions = range(len(words))
        
        bars = ax.barh(y_positions, counts, color='#00d9ff', edgecolor='#1a1a2e', linewidth=0.5)
        
        ax.set_yticks(y_positions)
        ax.set_yticklabels(words, color='#eee')
        ax.set_xlabel('Frequency', fontsize=11, color='#888')
        ax.set_title('Top Keywords', fontsize=14, color='#eee', pad=15)
        
        ax.invert_yaxis()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#444')
        ax.spines['left'].set_color('#444')
        
        plt.tight_layout()
        
        return self._save_chart(fig, output_path)
    
    def generate_engagement_chart(self, output_path=None):
        """Generate engagement trends monthly comparison"""
        data = self._get_engagement_stats()
        
        if not data['months']:
            return self._create_empty_chart("No Engagement Data")
        
        months = data['months']
        counts = data['counts']
        
        fig, ax = plt.subplots(figsize=(12, 5))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        
        ax.bar(months, counts, color='#9b59b6', edgecolor='#9b59b6', linewidth=0.5)
        
        # Add trend line
        if len(counts) > 1:
            z = np.polyfit(range(len(counts)), counts, 1)
            p = np.poly1d(z)
            ax.plot(months, p(range(len(counts))), '--', color='#00ff88', linewidth=2, label='Trend')
            ax.legend(facecolor='#1a1a2e', edgecolor='#444')
        
        ax.set_xlabel('Month', fontsize=11, color='#888')
        ax.set_ylabel('Activity Count', fontsize=11, color='#888')
        ax.set_title('Engagement Trends (Monthly)', fontsize=14, color='#eee', pad=15)
        
        plt.xticks(rotation=45, color='#888')
        plt.yticks(color='#888')
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#444')
        ax.spines['left'].set_color('#444')
        
        plt.tight_layout()
        
        return self._save_chart(fig, output_path)
    
    def _create_empty_chart(self, message):
        """Create an empty chart with a message"""
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor('#1a1a2e')
        ax.set_facecolor('#1a1a2e')
        ax.text(0.5, 0.5, message, ha='center', va='center', 
               fontsize=14, color='#666', transform=ax.transAxes)
        ax.axis('off')
        return self._save_chart(fig)
    
    def _save_chart(self, fig, output_path=None):
        """Save chart to file or return as base64"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, facecolor=fig.get_facecolor(),
                   edgecolor='none', bbox_inches='tight')
        buf.seek(0)
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(buf.getvalue())
            buf.close()
            plt.close(fig)
            return output_path
        else:
            img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
            plt.close(fig)
            return f"data:image/png;base64,{img_base64}"
    
    def generate_all_charts(self, output_dir):
        """Generate all charts and save to directory"""
        os.makedirs(output_dir, exist_ok=True)
        
        charts = {
            'activity.png': self.generate_activity_chart,
            'topics.png': self.generate_topic_chart,
            'actions.png': self.generate_action_completion_chart,
            'sources.png': self.generate_source_breakdown_chart,
            'keywords.png': self.generate_keywords_chart,
            'engagement.png': self.generate_engagement_chart
        }
        
        results = {}
        for filename, func in charts.items():
            filepath = os.path.join(output_dir, filename)
            try:
                func(filepath)
                results[filename] = {'status': 'success', 'path': filepath}
            except Exception as e:
                results[filename] = {'status': 'error', 'error': str(e)}
        
        return results


# Convenience function for API use
def generate_chart(chart_type, graph_data=None, output_path=None):
    """Generate a specific chart type"""
    engine = AnalyticsEngine(graph_data)
    
    chart_methods = {
        'activity': engine.generate_activity_chart,
        'topics': engine.generate_topic_chart,
        'actions': engine.generate_action_completion_chart,
        'sources': engine.generate_source_breakdown_chart,
        'keywords': engine.generate_keywords_chart,
        'engagement': engine.generate_engagement_chart
    }
    
    if chart_type not in chart_methods:
        raise ValueError(f"Unknown chart type: {chart_type}")
    
    return chart_methods[chart_type](output_path)


if __name__ == '__main__':
    # Test with sample data
    sample_data = {
        'graph': {
            'nodes': [
                {'id': '1', 'type': 'tweet', 'date': '2024-01-15', 'label': 'Test tweet'},
                {'id': '2', 'type': 'action', 'date': '2024-01-16', 'priority': 'high', 'status': 'done'},
                {'id': '3', 'type': 'topic', 'label': 'Python'},
            ],
            'edges': []
        },
        'actions': [
            {'priority': 'urgent', 'status': 'done'},
            {'priority': 'high', 'status': 'in_progress'},
            {'priority': 'medium', 'status': 'pending'},
            {'priority': 'low', 'status': 'pending'}
        ],
        'topics': {'Python': [1, 2], 'AI': [3], 'Code': [4]}
    }
    
    engine = AnalyticsEngine(sample_data)
    
    # Generate all charts
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        results = engine.generate_all_charts(tmpdir)
        print("Generated charts:", list(results.keys()))
        print("Stats:", json.dumps(engine.get_stats(), indent=2, default=str))
