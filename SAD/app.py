import streamlit as st
import pandas as pd
import requests
import pickle
import re

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.neighbors import NearestNeighbors

def clean_text(text):
    if pd.isnull(text):
        return ""
    text = text.lower()
    text = re.sub(r'[.,]', '', text)
    return text

@st.cache_data
def load_movies():
    with open('movies_info.pkl', 'rb') as f:
        return pickle.load(f)

@st.cache_data
def load_rated_movies():
    with open('rated_movies.pkl', 'rb') as f:
        return pickle.load(f)

@st.cache_resource
def get_vectorizer_and_knn(movies):
    movies = movies.fillna('')
    movies['features'] = (
        movies['genres'].astype(str) + ' ' +
        movies['keywords'].astype(str) + ' ' +
        movies['title'].astype(str) + ' ' +
        movies['overview'].astype(str)
    )
    movies['features'] = movies['features'].apply(clean_text) 
    vectorizer = CountVectorizer(token_pattern=r"(?u)\b\w+\b")
    X = vectorizer.fit_transform(movies['features'])
    knn = NearestNeighbors(metric='cosine', algorithm='brute')
    knn.fit(X)
    return vectorizer, knn, X

@st.cache_data
def fetch_poster(movie_id, release_year):
    api_key = '34d72a2f52be7a84916976ed820a3adc'  
    url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tmdb_year = data.get('release_date', '')[:4]
        if str(release_year) == str(tmdb_year):
            poster_path = data.get('poster_path')
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
    return "https://via.placeholder.com/220x330?text=No+Poster"
  

movies = load_movies()
rated_movies = load_rated_movies()

# Adiciona coluna title_year se não existir
if 'title_year' not in movies.columns:
    movies['title_year'] = movies['title'] + ' (' + movies['year'].astype(str) + ')'

vectorizer, knn, X = get_vectorizer_and_knn(movies)

def get_recommendations_by_content(title_year, n_recommendations=40):
    if title_year not in movies['title_year'].values:
        return []
    idx = movies[movies['title_year'] == title_year].index[0]
    distances, indices = knn.kneighbors(X[idx], n_neighbors=n_recommendations+1)
    recommended_title_years = [movies.iloc[i]['title_year'] for i in indices.flatten() if movies.iloc[i]['title_year'] != title_year]
    return recommended_title_years[:n_recommendations]

def get_recommendation_by_ratings(title_year, n_recommendations=18):
    content_recs = get_recommendations_by_content(title_year, n_recommendations=140)
    if not content_recs:
        return []
    pivot = rated_movies.pivot_table(index='title_year', columns='user_id', values='rating').fillna(0)
    filtered_titles = [title_year] + [rec for rec in content_recs if rec in pivot.index]
    filtered_pivot = pivot.loc[filtered_titles]
    knn_ratings = NearestNeighbors(metric='cosine', algorithm='brute')
    knn_ratings.fit(filtered_pivot.values)
    idx = filtered_pivot.index.get_loc(title_year)
    distances, indices = knn_ratings.kneighbors([filtered_pivot.iloc[idx].values], n_neighbors=min(n_recommendations+1, len(filtered_titles)))
    recommended_title_years = [filtered_pivot.index[i] for i in indices.flatten() if filtered_pivot.index[i] != title_year]
    return recommended_title_years[:n_recommendations]

def show_posters_grid(recommendations):
    recommendations = recommendations.drop_duplicates(subset='title_year').reset_index(drop=True)
    num_to_show = min(6, len(recommendations))
    for i in range(0, num_to_show, 3):
        cols = st.columns(3)
        for idx, col in enumerate(cols):
            j = i + idx
            if j < num_to_show:
                movie_title = recommendations.iloc[j]['title']
                movie_id = recommendations.iloc[j]['movie_id']
                year = recommendations.iloc[j]['year']
                title_year = recommendations.iloc[j]['title_year']
                poster_url = fetch_poster(movie_id, year)
                with col:
                    st.image(poster_url, width=400)
                    st.write(f"{title_year}")

with st.sidebar:
    st.title("Sistema de Recomendação")
    search_input = st.text_input("Digite parte do nome do filme:")

    if search_input:
        filtered_titles = movies[movies['title_year'].str.lower().str.contains(search_input.lower(), na=False)]['title_year'].unique()
        if len(filtered_titles) == 0:
            st.warning("Nenhum filme encontrado.")
            selected_movie = None
        else:
            selected_movie = st.selectbox("Selecione o filme:", filtered_titles)
    else:
        selected_movie = None

    rec_system = st.checkbox("Usar recomendação por notas dos usuários", value=False)

    if selected_movie:
        movie_row = movies[movies['title_year'] == selected_movie]
        if not movie_row.empty:
            movie_id = movie_row.iloc[0]['id']
            year = movie_row.iloc[0]['year']
            poster_url = fetch_poster(movie_id, year)
            st.markdown(
                f"<div style='display: flex; justify-content: center;'><img src='{poster_url}' width='220'></div><br>",
                unsafe_allow_html=True
            )
    recommend_clicked = st.button('Recomendar', use_container_width=True)

st.markdown("""<h1 style='font-weight:bold;'><span style='color:#D7263D;'>REC.</span><span style='color:#f8f8f8;'>mendar</span> :</h1>""", unsafe_allow_html=True)

if selected_movie and recommend_clicked:
    if not rec_system:
        st.subheader("Recomendações por conteúdo:")
        recommendations = get_recommendations_by_content(selected_movie)
        rec_df = movies[movies['title_year'].isin(recommendations)][['title', 'id', 'year', 'title_year']].rename(columns={'id': 'movie_id'}).reset_index(drop=True)
        show_posters_grid(rec_df)
    else:
        st.subheader("Recomendações por notas de usuários:")
        recommendations = get_recommendation_by_ratings(selected_movie)
        rec_df = movies[movies['title_year'].isin(recommendations)][['title', 'id', 'year', 'title_year']].rename(columns={'id': 'movie_id'}).reset_index(drop=True)
        show_posters_grid(rec_df)