#python app.py

from flask import Flask,jsonify , request
import sqlite3
from flask_cors import CORS
import os

# Ensure db_file is defined globally
db_file = os.getenv('DB_FILE', 'SenzoQuizAppDB20feb2024.db')


app = Flask(__name__)
app.json.sort_keys = False
CORS(app)
def execute_query(query):
    conn = sqlite3.connect(db_file)
    if not conn:
        raise Exception("Connection not established. Call connect() method first.")
    
    cursor = conn.cursor()
    cursor.execute(query)
    result_set = cursor.fetchall()
    conn.close()
    return result_set

@app.route("/start_quize", methods=['GET','POST'])
def start_quize():
    allGenres = {}
    query = f""" SELECT genres.genre_id,genres.genre_name from genres """
    dbesponse = execute_query(query)
    
    genersList = []
    for resp in dbesponse:
        temp = {}
        temp["GenreID"] = resp[0]
        temp["GenreName"] = resp[1]
        genersList.append(temp)
    allGenres["which genre do you want to see?"] = genersList
    return allGenres

@app.route("/load_quize/<genreids>", methods=['GET','POST'])
def load_quize(genreids):
    quiz = {}
    mianQuestionair = []

    query1 = f"""SELECT genres.genre_id, genres.genre_name from genres WHERE genres.genre_id IN ({str(genreids)})"""
    results1 = execute_query(query1)
    for result1 in results1:
        genredata  = {}
        genredata["GenreID"] = result1[0]
        genredata["GenreName"] = result1[1]
        genredata["GenreQuestion"] = []
        
        query2 = f"""SELECT genre_questions.gener_question_id, genre_questions.gener_question FROM genre_questions WHERE genre_id = {result1[0]}"""
        results2 = execute_query(query2)
        
        
        for result2 in results2:
            tempQuestion = {}
            tempQuestion["GenreQuestionID"] = result2[0]
            tempQuestion["GenreQuestionText"] = result2[1]
            

            query3 = f"""SELECT sub_genres.sub_genre_id, sub_genres.sub_genre_name FROM sub_genres WHERE  sub_genres.gener_question_id = {result2[0]} AND sub_genres.genre_id = {result1[0]}"""
            results3 = execute_query(query3)
            
            tempQuestion["SubGenresList"] = []
            
            for result3 in results3:
                tempSubGenres = {}
                tempSubGenres["SubGenreID"] = result3[0]
                tempSubGenres["SubGenreName"] = result3[1]

                query4 = f"""SELECT sub_genre_questions.sub_genre_question_id, sub_genre_questions.sub_genre_question_txt FROM sub_genre_questions WHERE sub_genre_questions.sub_genre_id = {result3[0]} AND sub_genre_questions.genre_id = {result1[0]}"""
                results4 = execute_query(query4)
                tempSubGenres["SubGenreQuestionsList"] = []

                for result4 in results4:
                    tempSubGenreQuestions = {}
                    tempSubGenreQuestions["SubGenreQuestionID"] = result4[0]
                    tempSubGenreQuestions["SubGenreQuestionName"] = result4[1]
                    tempSubGenreQuestions["PlotTypeList"] = []

                    query5 = f"""SELECT attributes.attribute_id, attributes.attribute_name FROM attributes WHERE attributes.sub_genre_id = {result3[0]} AND attributes.sub_genre_question_id = {result4[0]}"""
                    results5 = execute_query(query5)
                    
                    
                    for result5 in results5:
                        attributes = {}
                        attributes["AttributeID"] = result5[0]
                        attributes["AttributeName"] = result5[1]

                        tempSubGenreQuestions["PlotTypeList"].append(attributes)

                    tempSubGenres["SubGenreQuestionsList"].append(tempSubGenreQuestions)

                tempQuestion["SubGenresList"].append(tempSubGenres)

            genredata["GenreQuestion"].append(tempQuestion)

        mianQuestionair.append(genredata)
    
    quiz["Questionair List"] = mianQuestionair
    return jsonify(quiz)



@app.route('/recommendation', methods=['GET','POST'])
def get_recommendation():
    
    movies = {}

    if not request.is_json:
        return jsonify({"error": "Request must be in JSON format"}), 400
    
    data = request.get_json()

    required_keys = ["Genres", "SubGenres", "PlotTypes"]
    for key in required_keys:
        if key not in data:
            return jsonify({"error": f"Missing key: {key}"}), 400
    

    genres = ','.join(map(str, data["Genres"]))
    subGenres = ','.join(map(str, data["SubGenres"]))
    plotTypes = ','.join(map(str, data["PlotTypes"]))

    query1 = f"""SELECT genres.genre_name from genres WHERE genres.genre_id IN ({genres});"""
    query2 = f"""SELECT sub_genres.sub_genre_name from sub_genres WHERE sub_genres.sub_genre_id IN ({subGenres});"""
    query3 = f"""SELECT attributes.attribute_name from attributes WHERE attributes.attribute_id IN ({plotTypes});"""
    
    result1 = [f"{temp[0]}" for temp in execute_query(query1)]
    result2 = [f"{temp[0]}" for temp in execute_query(query2)]
    result3 = [f"{temp[0]}" for temp in execute_query(query3)]
    
    genreConditions = ""
    subgenreCondition = ""
    plotTypesCondition = ""
    if len(result1)>0:
        temp = []
        for r in result1:
            temp.append(f"""genres LIKE '%{r}%'""")
        genreConditions = f"WHERE {' OR '.join(temp)}"
    
    if len(result2) > 0:
        temp = []
        for r in result2:
            temp.append(f"""subGenres LIKE '%{r}%'""")
        subgenreCondition = f"""
                            WHERE EXISTS (
                                SELECT 1
                                FROM movies
                                WHERE {' OR '.join(temp)}
                                AND first_query.movie_id = movies.movie_id
                            )
                            """
    
    
    if len(result3) > 0:
        temp = []
        for r in result3:
            temp.append(f"""plotTypes LIKE '%{r}%'""")
        plotTypesCondition = f"""
                            AND EXISTS (
                                SELECT 1
                                FROM movies
                                WHERE {' OR '.join(temp)}
                                AND first_query.movie_id = movies.movie_id
                            )
                            """
    
    
    query4 = f"""
                SELECT movie_id, movie_name, release_year, tmdb_rating, genres, subGenres, plotTypes
                FROM (
                    SELECT movie_id, movie_name, release_year, tmdb_rating, genres, subGenres, plotTypes
                    FROM movies
                {genreConditions}
                ) AS first_query 
                {subgenreCondition} 
                {plotTypesCondition}
            """
    
    result4 = execute_query(query4)
    
    recommendation = []
    for movie in result4:
        movie_details = {}
        movie_details["MovieId"] = movie[0]
        movie_details["MovieName"] = movie[1]
        movie_details["ReleaseYear"] = movie[2]
        movie_details["TmdbRating"] = movie[3]
        movie_details["MovieGenre"] = movie[4]
        movie_details["MovieSubGenre"] = movie[5]
        movie_details["MoviePlotTypes"] = movie[6]
        recommendation.append(movie_details)
    
    movies["Recommendations"] = recommendation
    return jsonify(movies)

#this end point will be return us genre, subgenre and plottype using movie name
@app.route('/genre_subgenre_plottype', methods=['GET','POST'])
def get_genre_subgenre_plottype():
    if not request.is_json:
        return jsonify({"error": "Request must be in JSON format"}), 400
    
    data = request.get_json()

    required_keys = ["Movie Name"]
    for key in required_keys:
        if key not in data:
            return jsonify({"error": f"Missing key: {key}"}), 400
    movieName = data["Movie Name"]

    query = f"""SELECT movies.genres, movies.subGenres, movies.plotTypes FROM movies WHERE movies.movie_name = "{movieName}";"""
    result = execute_query(query)
    movieData = result[0]

    subgenre = movieData[1].split(',')
    plotType = movieData[2].split(',')

    movie_dict = {
        "genre": movieData[0],
        "subgenre": subgenre,
        "plotType": plotType
    }

    return jsonify(movie_dict)


if __name__ == '__main__':
    db_file = r"D:\Senzoo\senzo-frontend\SenzoQuizAppDB20feb2024"
    app.run(debug=True)
