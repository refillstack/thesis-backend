-- Create papers table
create table if not exists papers (
    id uuid primary key,
    file_url text not null,
    filename text not null,
    content_type text not null,
    extracted_text text,
    paper_analysis jsonb,  -- Stores the comprehensive paper analysis
    citation_analysis jsonb,  -- Stores citation analysis
    gap_analysis jsonb,  -- Stores research gaps analysis
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- Create a view for easier querying of paper analysis
create or replace view paper_summaries as
select 
    id,
    file_url,
    filename,
    paper_analysis->'basic_info'->>'title' as title,
    paper_analysis->'basic_info'->'authors' as authors,
    paper_analysis->'basic_info'->>'year_of_publication' as year_of_publication,
    paper_analysis->'basic_info'->>'type' as paper_type,
    paper_analysis->'analysis'->>'relevance_score' as relevance_score,
    paper_analysis->'analysis'->'main_findings' as main_findings,
    paper_analysis->'analysis'->'methods'->>'methodology_type' as methodology,
    paper_analysis->'analysis'->'gaps_and_limitations'->'identified_gaps' as gaps,
    paper_analysis->'meta_info'->>'reviewer_initials' as reviewer_initials,
    paper_analysis->'basic_info'->>'link_to_article' as article_link,
    created_at,
    updated_at
from papers;

-- Create function to update updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Create trigger to automatically update updated_at
create trigger update_papers_updated_at
    before update on papers
    for each row
    execute function update_updated_at_column(); 