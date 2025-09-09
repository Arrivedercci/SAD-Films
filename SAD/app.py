import streamlit as st
import pandas as pd
import requests
import pickle
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv() 

# pasta onde estão este script e os .pkl
BASE_DIR = Path(__file__).resolve().parent  # ...\SAD-Films\SAD
MOVIES_PKL   = BASE_DIR / "movies_info.pkl"
CONTENT_RECS_PKL = BASE_DIR / "content_recs.pkl"
RATING_RECS_PKL = BASE_DIR / "rating_recs.pkl"

def load_movies():
    if not MOVIES_PKL.exists():
        st.error(f"Arquivo não encontrado: {MOVIES_PKL}")
        return pd.DataFrame()
    with open(MOVIES_PKL, "rb") as f:
        return pickle.load(f)

def load_recommendations(file_path):
    if not file_path.exists():
        st.error(f"Arquivo não encontrado: {file_path}")
        return {}
    with open(file_path, "rb") as f:
        return pickle.load(f)

movies = load_movies()
content_recs = load_recommendations(CONTENT_RECS_PKL)
rating_recs = load_recommendations(RATING_RECS_PKL)

def fetch_poster(movie_id, release_year):
    api_key = os.getenv('API_KEY')
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
  

# Adiciona coluna title_year se não existir
if 'title_year' not in movies.columns:
    movies['title_year'] = movies['title'] + ' (' + movies['year'].astype(str) + ')'

def get_recommendations_by_content(title_year, n_recommendations=80):
    if title_year not in content_recs:
        return []
    return content_recs[title_year][:n_recommendations]

def get_recommendation_by_ratings(title_year, n_recommendations=18):
    if title_year not in rating_recs:
        return []
    return rating_recs[title_year][:n_recommendations]

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