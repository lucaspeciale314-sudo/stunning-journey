#!/usr/bin/env python3
"""
Letterboxd Movie Exporter & List Generator
Filters movies by rating, liked status, and other criteria,
then exports them in a format importable by Letterboxd.
"""

import csv
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Movie:
    """Represents a Letterboxd movie entry."""
    name: str
    year: int
    letterboxd_uri: str
    tmdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    rating: Optional[float] = None
    date: Optional[str] = None
    tags: Optional[str] = None


class LetterboxdExporter:
    """Export and filter Letterboxd movies."""
    
    def __init__(self, csv_file: Path):
        """Initialize with a CSV export from Letterboxd."""
        self.csv_file = csv_file
        self.movies: List[Movie] = []
        self._load_csv()
    
    def _load_csv(self) -> None:
        """Load movies from Letterboxd CSV export."""
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        rating = float(row.get('Rating', '')) if row.get('Rating') else None
                    except ValueError:
                        rating = None
                    
                    movie = Movie(
                        name=row.get('Name', ''),
                        year=int(row.get('Year', 0)) if row.get('Year') else 0,
                        letterboxd_uri=row.get('Letterboxd URI', ''),
                        tmdb_id=row.get('TMDb Id'),
                        imdb_id=row.get('IMDb Id'),
                        rating=rating,
                        date=row.get('Date'),
                        tags=row.get('Tags')
                    )
                    self.movies.append(movie)
            print(f"✓ Loaded {len(self.movies)} movies from {self.csv_file.name}")
        except FileNotFoundError:
            print(f"✗ File not found: {self.csv_file}")
            raise
        except Exception as e:
            print(f"✗ Error loading CSV: {e}")
            raise
    
    def filter_by_rating(self, movies: List[Movie], rating: float) -> List[Movie]:
        """Filter movies by exact rating."""
        filtered = [m for m in movies if m.rating and m.rating == rating]
        return filtered
    
    def filter_by_rating_range(self, movies: List[Movie], min_rating: float, max_rating: float) -> List[Movie]:
        """Filter movies by rating range (inclusive)."""
        filtered = [
            m for m in movies
            if m.rating and m.rating >= min_rating and m.rating <= max_rating
        ]
        return filtered
    
    def filter_by_year(self, movies: List[Movie], start_year: int, end_year: Optional[int] = None) -> List[Movie]:
        """Filter movies by year released."""
        filtered = [
            m for m in movies
            if m.year >= start_year
            and (end_year is None or m.year <= end_year)
        ]
        return filtered
    
    def filter_by_tags(self, movies: List[Movie], tags: List[str], match_all: bool = False) -> List[Movie]:
        """Filter movies by tags. If match_all=True, requires all tags."""
        filtered = []
        for movie in movies:
            if not movie.tags:
                continue
            movie_tags = set(tag.strip().lower() for tag in movie.tags.split(','))
            search_tags = set(tag.lower() for tag in tags)
            
            if match_all:
                if search_tags.issubset(movie_tags):
                    filtered.append(movie)
            else:
                if search_tags.intersection(movie_tags):
                    filtered.append(movie)
        
        return filtered
    
    def export_to_csv(self, movies: List[Movie], output_file: Path, include_ratings: bool = True) -> None:
        """Export movies to CSV in Letterboxd-compatible format."""
        fieldnames = ['Name', 'Year', 'Letterboxd URI']
        if include_ratings:
            fieldnames.extend(['TMDb Id', 'IMDb Id', 'Rating'])
        fieldnames.extend(['Tags'])
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for movie in movies:
                    row = {
                        'Name': movie.name,
                        'Year': movie.year,
                        'Letterboxd URI': movie.letterboxd_uri,
                    }
                    if include_ratings:
                        row['TMDb Id'] = movie.tmdb_id or ''
                        row['IMDb Id'] = movie.imdb_id or ''
                        row['Rating'] = movie.rating or ''
                    row['Tags'] = movie.tags or ''
                    
                    writer.writerow(row)
            
            print(f"✓ Exported {len(movies)} movies to {output_file.name}")
        except Exception as e:
            print(f"✗ Error exporting CSV: {e}")
            raise
    
    def export_to_txt(self, movies: List[Movie], output_file: Path) -> None:
        """Export as plain text list (one URI per line for Letterboxd import)."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for movie in movies:
                    f.write(f"{movie.letterboxd_uri}\n")
            print(f"✓ Exported {len(movies)} URIs to {output_file.name}")
        except Exception as e:
            print(f"✗ Error exporting text: {e}")
            raise
    
    def display_summary(self, movies: List[Movie]) -> None:
        """Display a summary of the filtered movies."""
        print(f"\n{'='*70}")
        print(f"SUMMARY: {len(movies)} movies")
        print(f"{'='*70}\n")
        
        avg_rating = (
            sum(m.rating for m in movies if m.rating) / 
            len([m for m in movies if m.rating])
            if any(m.rating for m in movies) else 0
        )
        
        print(f"Average Rating: {avg_rating:.2f}")
        print(f"\nTop 10 Movies:")
        print(f"{'─'*70}")
        
        sorted_movies = sorted(
            [m for m in movies if m.rating],
            key=lambda x: x.rating,
            reverse=True
        )[:10]
        
        for i, movie in enumerate(sorted_movies, 1):
            print(f"{i:2d}. {movie.name} ({movie.year}) - {movie.rating}★")
        
        print(f"{'='*70}\n")


def parse_rating_arg(rating_str: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse rating argument in format:
    - "4.5" -> (4.5, None) for exact rating
    - "3.0:5.0" -> (3.0, 5.0) for range
    - "3.0:" -> (3.0, None) for minimum rating
    
    Returns: (min_rating, max_rating) tuple
    """
    if ':' in rating_str:
        parts = rating_str.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid rating range format: {rating_str}. Use 'X:Y' or 'X:'")
        
        min_val = float(parts[0]) if parts[0] else None
        max_val = float(parts[1]) if parts[1] else None
        
        if min_val is None and max_val is None:
            raise ValueError("At least one value required in rating range")
        
        if min_val and max_val and min_val > max_val:
            raise ValueError(f"Min rating ({min_val}) cannot be greater than max ({max_val})")
        
        return (min_val, max_val)
    else:
        # Exact rating
        return (float(rating_str), float(rating_str))


def main():
    parser = argparse.ArgumentParser(
        description="Export and filter movies from Letterboxd CSV exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export movies with exactly 4.5 stars
  python letterboxd_exporter.py ratings.csv -r 4.5
  
  # Export movies rated between 3.0 and 5.0 stars
  python letterboxd_exporter.py ratings.csv -r 3.0:5.0
  
  # Export movies rated 4.0 stars or higher
  python letterboxd_exporter.py ratings.csv -r 4.0:
  
  # Export 4+ star movies from 2015 onwards
  python letterboxd_exporter.py ratings.csv -r 4.0: --year-from 2015
  
  # Export as plain text (URIs only)
  python letterboxd_exporter.py ratings.csv -r 4.0:5.0 --txt
        """
    )
    
    parser.add_argument(
        'csv_file',
        type=Path,
        help='Path to your Letterboxd CSV export (e.g., ratings.csv, watched.csv)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('filtered_movies.csv'),
        help='Output file name (default: filtered_movies.csv)'
    )
    
    parser.add_argument(
        '-r', '--rating',
        type=str,
        help="""
            Rating filter. Format options:
            - Single value (e.g., "4.5"): exact rating
            - Range (e.g., "3.0:5.0"): min to max (inclusive)
            - Open range (e.g., "4.0:"): minimum and above
            - Open range (e.g., ":4.0"): maximum and below
        """
    )
    
    parser.add_argument(
        '--year-from',
        type=int,
        help='Filter movies from this year onwards'
    )
    
    parser.add_argument(
        '--year-to',
        type=int,
        help='Filter movies up to this year'
    )
    
    parser.add_argument(
        '--tags',
        type=str,
        help='Filter by comma-separated tags (e.g., "sci-fi,adventure")'
    )
    
    parser.add_argument(
        '--txt',
        action='store_true',
        help='Export as plain text (one URI per line) for Letterboxd import'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        default=False,
        help='Display summary statistics'
    )
    
    args = parser.parse_args()
    
    # Load CSV
    exporter = LetterboxdExporter(args.csv_file)
    
    # Start with all movies
    filtered = exporter.movies
    
    # Apply filters
    if args.rating:
        try:
            min_rating, max_rating = parse_rating_arg(args.rating)
            
            if min_rating == max_rating:
                # Exact rating
                filtered = exporter.filter_by_rating(filtered, min_rating)
                print(f"✓ Filtered by exact rating = {min_rating}: {len(filtered)} movies")
            else:
                # Range
                if min_rating is None:
                    min_rating = 0.0
                if max_rating is None:
                    max_rating = 5.0
                filtered = exporter.filter_by_rating_range(filtered, min_rating, max_rating)
                print(f"✓ Filtered by rating {min_rating}-{max_rating}: {len(filtered)} movies")
        except ValueError as e:
            print(f"✗ Invalid rating argument: {e}")
            return
    
    if args.year_from or args.year_to:
        year_from = args.year_from or 0
        year_to = args.year_to
        filtered = exporter.filter_by_year(filtered, year_from, year_to)
        print(f"✓ Filtered by year {year_from}-{year_to or 'present'}: {len(filtered)} movies")
    
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',')]
        filtered = exporter.filter_by_tags(filtered, tags)
        print(f"✓ Filtered by tags {tags}: {len(filtered)} movies")
    
    # Export
    if args.txt:
        output_file = args.output.with_suffix('.txt')
        exporter.export_to_txt(filtered, output_file)
    else:
        exporter.export_to_csv(filtered, args.output)
    
    # Display summary
    if args.summary and filtered:
        exporter.display_summary(filtered)


if __name__ == '__main__':
    main()