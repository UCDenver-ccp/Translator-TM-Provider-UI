from flask import Flask, render_template, request
import os
import urllib
import models
import services
import json

app = Flask(__name__)
username = os.getenv('MYSQL_DATABASE_USER', None)
secret_password = os.getenv('MYSQL_DATABASE_PASSWORD', None)
assert username
assert secret_password
models.init_db(username=username, password=secret_password)
s = models.session()


@app.route('/')
def index():
    subjects = [sub[0] for sub in s.query(models.Assertion.subject_curie).distinct()]
    predicates = [pre[0] for pre in s.query(models.EvidenceScore.predicate_curie).distinct()]
    objects = [obj[0] for obj in s.query(models.Assertion.object_curie).distinct()]
    return render_template("mockup.html", subjects=subjects, predicates=predicates, objects=objects)


@app.route('/query/', methods=['POST'], strict_slashes=False)
def query():
    if request.is_json:
        request_dict = json.loads(request.data)
        subject_curie = request_dict['subject']
        predicate_curie = request_dict['predicate']
        object_curie = request_dict['object']
        assertion_list = s.query(models.Assertion).where(models.Assertion.subject_curie == subject_curie, models.Assertion.object_curie == object_curie)
        edges = []
        for edge in get_edge_list(assertion_list):
            if edge["predicate_curie"] == predicate_curie:
                edges.append(edge)
        normalized_nodes = services.get_normalized_nodes([subject_curie, object_curie])
        results = {
            "query": {
                "subject_curie": subject_curie,
                "subject_text": normalized_nodes[subject_curie],
                "predicate_curie": predicate_curie,
                "object_curie": object_curie,
                "object_text": normalized_nodes[object_curie],
            },
            "results": edges
        }
        return json.dumps(results), 200
    return 'something else', 400


def get_edge_list(assertions):
    edge_list = []
    for assertion in assertions:
        predicate_list = assertion.get_predicates()  # these are the predicates that have the high score for at least one evidence
        for predicate in predicate_list:
            for ev in assertion.evidence_list:
                if ev.get_top_predicate() == predicate:
                    edge_list.append({
                        "document_pmid": ev.document_id,
                        "document_zone": ev.document_zone,
                        "document_year": ev.document_year_published,
                        "predicate_curie": predicate,
                        "confidence_score": ev.get_score(predicate),
                        "sentence": ev.sentence,
                        "subject_span": ev.subject_entity.span,
                        "object_span": ev.object_entity.span
                    })
    return edge_list


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
