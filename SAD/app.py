import streamlit as st
import pandas as pd
import requests
import pickle

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.neighbors import NearestNeighbors

with open('movies_info.pkl', 'rb') as f:
    movies = pickle.load(f)

with open('rated_movies.pkl', 'rb') as f:
    rated_movies = pickle.load(f)



movies = movies.fillna('')

movies['features'] = (
    movies['director'].astype(str) + ' ' +
    movies['genres_y'].astype(str) + ' ' +
    movies['keywords'].astype(str)
)


vectorizer = CountVectorizer(token_pattern=r"(?u)\b\w+\b")
X = vectorizer.fit_transform(movies['features'])

knn = NearestNeighbors(metric='cosine', algorithm='brute')
knn.fit(X)

def get_recommendations_by_content(title, n_recommendations=50):
    if title not in movies['title_x'].values:
        return f"Filme '{title}' não encontrado."
    
    idx = movies[movies['title_x'] == title].index[0]
    distances, indices = knn.kneighbors(X[idx], n_neighbors=n_recommendations+1)
    
    recommended_titles = [movies.iloc[i]['title_x'] for i in indices.flatten() if movies.iloc[i]['title_x'] != title]
    return recommended_titles[:n_recommendations]

def get_recommendation_by_ratings(title, n_recommendations=6):
    content_recs = get_recommendations_by_content(title, n_recommendations=50)
    if not content_recs:
        return f"Filme '{title}' não encontrado."
    
    pivot = rated_movies.pivot_table(index='film_title', columns='user_id', values='rating').fillna(0)
    
    filtered_titles = [title] + [rec for rec in content_recs if rec in pivot.index]
    filtered_pivot = pivot.loc[filtered_titles]
    
    knn_ratings = NearestNeighbors(metric='cosine', algorithm='brute')
    knn_ratings.fit(filtered_pivot.values)
    
    idx = filtered_pivot.index.get_loc(title)
    distances, indices = knn_ratings.kneighbors([filtered_pivot.iloc[idx].values], n_neighbors=min(n_recommendations+1, len(filtered_titles)))
    
    recommended_titles = [filtered_pivot.index[i] for i in indices.flatten() if filtered_pivot.index[i] != title]
    return recommended_titles[:n_recommendations]

def fetch_poster(movie_id):
    api_key = '34d72a2f52be7a84916976ed820a3adc'  
    url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}'
    response = requests.get(url)
    data = response.json()
    poster_path = data['poster_path']
    full_path = f"https://image.tmdb.org/t/p/w500{poster_path}"
    return full_path

def show_posters_grid(recommendations):
    recommendations = recommendations.drop_duplicates(subset='title').reset_index(drop=True)
    num_to_show = min(6, len(recommendations))
    for i in range(0, num_to_show, 3):
        cols = st.columns(3)
        for idx, col in enumerate(cols):
            j = i + idx
            if j < num_to_show:
                movie_title = recommendations.iloc[j]['title']
                movie_id = recommendations.iloc[j]['movie_id']
                poster_url = fetch_poster(movie_id)
                with col:
                    st.image(poster_url, width=400)
                    st.write(movie_title)

                    
with st.sidebar:
    st.title("Sistema de Recomendação")
    search_input = st.text_input("Digite parte do nome do filme:")

    if search_input:
        filtered_titles = movies[movies['title_x'].str.lower().str.contains(search_input.lower())]['title_x'].unique()
        if len(filtered_titles) == 0:
            st.warning("Nenhum filme encontrado.")
            selected_movie = None
        else:
            selected_movie = st.selectbox("Selecione o filme:", filtered_titles)
    else:
        selected_movie = None

    rec_system = st.checkbox("Usar recomendação por notas dos usuários", value=False)

    if selected_movie:
        movie_row = movies[movies['title_x'] == selected_movie]
        if not movie_row.empty:
            movie_id = movie_row.iloc[0]['id']
            poster_url = fetch_poster(movie_id)
            st.markdown(
                f"<div style='display: flex; justify-content: center;'><img src='{poster_url}' width='220'></div><br>",
                unsafe_allow_html=True
            )
    recommend_clicked = st.button('Recomendar', use_container_width=True)

st.markdown("<h1 style='color:#D7263D; font-weight:bold;'>XUXU FILMES:</h1>", unsafe_allow_html=True)

if selected_movie and recommend_clicked:
    if not rec_system:
        st.subheader("Recomendações por conteúdo:")
        recommendations = get_recommendations_by_content(selected_movie)
        rec_df = movies[movies['title_x'].isin(recommendations)][['title_x', 'id']].rename(columns={'title_x': 'title', 'id': 'movie_id'}).reset_index(drop=True)
        show_posters_grid(rec_df)
    else:
        st.subheader("Recomendações por notas de usuários:")
        recommendations = get_recommendation_by_ratings(selected_movie)
        rec_df = movies[movies['title_x'].isin(recommendations)][['title_x', 'id']].rename(columns={'title_x': 'title', 'id': 'movie_id'}).reset_index(drop=True)
        show_posters_grid(rec_df)