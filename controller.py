from flask import Flask, render_template, request
from sqlalchemy import or_
import os
import urllib
import models
import services
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template("mockup.html", subjects=subjects, predicates=predicates, objects=objects)

@app.route('/public/', strict_slashes=False)
def public_index():
    return render_template("mockup.html", subjects=subjects, predicates=predicates, objects=objects)

@app.route('/translator/', strict_slashes=False)
def translator_index():
    return render_template("mockup.html", subjects=subjects_uniprot, predicates=predicates, objects=objects_uniprot)


@app.route('/query/', methods=['POST'], strict_slashes=False)
def query():
    if request.is_json:
        request_dict = json.loads(request.data)
        subject_curie = request_dict['subject']
        predicate_curie = request_dict['predicate']
        object_curie = request_dict['object']
        assertion_list = []
        if subject_curie == 'Any':
            if object_curie == 'Any':
                assertion_list = s.query(models.Assertion)
            else:
                if object_curie.startswith('UniProtKB'):
                    assertion_list = s.query(models.Assertion).where(models.Assertion.object_uniprot.has(models.PRtoUniProt.uniprot == object_curie))
                else:
                    assertion_list = s.query(models.Assertion).where(models.Assertion.object_curie == object_curie)
        else:
            if(object_curie == 'Any'):
                if subject_curie.startswith('UniProtKB'):
                    assertion_list = s.query(models.Assertion).where(models.Assertion.subject_uniprot.has(models.PRtoUniProt.uniprot == subject_curie))
                else:
                    assertion_list = s.query(models.Assertion).where(models.Assertion.subject_curie == subject_curie)
            else:
                if object_curie.startswith('UniProtKB'):
                    if subject_curie.startswith('UniProtKB'):
                        assertion_list = s.query(models.Assertion).where(models.Assertion.object_uniprot.has(models.PRtoUniProt.uniprot == object_curie), models.Assertion.subject_uniprot.has(models.PRtoUniProt.uniprot == subject_curie))
                    else:
                        assertion_list = s.query(models.Assertion).where(models.Assertion.object_uniprot.has(models.PRtoUniProt.uniprot == object_curie), models.Assertion.subject_curie == subject_curie)
                else:
                    if subject_curie.startswith('UniProtKB'):
                        assertion_list = s.query(models.Assertion).where(models.Assertion.object_curie == object_curie, models.Assertion.subject_uniprot.has(models.PRtoUniProt.uniprot == subject_curie))
                    else:
                        assertion_list = s.query(models.Assertion).where(models.Assertion.subject_curie == subject_curie, models.Assertion.object_curie == object_curie)
        edges = []
        for edge in get_edge_list(assertion_list, use_uniprot=(subject_curie.startswith('UniProtKB') or object_curie.startswith('UniProtKB'))):
            if edge["predicate_curie"] == predicate_curie or predicate_curie == 'Any':
                edges.append(edge)
        normalized_nodes = services.get_normalized_nodes([subject_curie, object_curie])
        edges.sort(key=lambda x: x['confidence_score'], reverse=True)
        results = {
            "query": {
                "subject_curie": subject_curie,
                "subject_text": normalized_nodes[subject_curie] if subject_curie in normalized_nodes else subject_curie,
                "predicate_curie": predicate_curie,
                "object_curie": object_curie,
                "object_text": normalized_nodes[object_curie] if object_curie in normalized_nodes else object_curie,
            },
            "results": edges[:EDGE_LIMIT]
        }
        return json.dumps(results), 200
    return 'something else', 400


def get_edge_list(assertions, use_uniprot=False):
    edge_list = []
    for assertion in assertions:
        sub = assertion.subject_curie
        obj = assertion.object_curie
        if use_uniprot:
            if assertion.subject_uniprot:
                sub = assertion.subject_uniprot.uniprot
            if assertion.object_uniprot:
                obj = assertion.object_uniprot.uniprot
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
                        "object_span": ev.object_entity.span,
                        "subject_curie": sub,
                        "object_curie": obj
                    })
    return edge_list


def get_options() -> (list, list, list):
    subject_curies = [sub[0] for sub in s.query(models.Assertion.subject_curie).distinct()]
    predicate_curies = [pre[0] for pre in s.query(models.EvidenceScore.predicate_curie).distinct()]
    object_curies = [obj[0] for obj in s.query(models.Assertion.object_curie).distinct()]
    list_to_normalize = []
    subjects = []
    objects = []
    list_to_normalize.extend(subject_curies)
    list_to_normalize.extend(object_curies)
    normalized_nodes = services.get_normalized_nodes(list_to_normalize)
    for subject in subject_curies:
        if subject in normalized_nodes and normalized_nodes[subject] is not None:
            subjects.append((subject, normalized_nodes[subject]["id"]["label"]))
        else:
            subjects.append((subject, subject))
    for obj in object_curies:
        if obj in normalized_nodes and normalized_nodes[obj] is not None:
            objects.append((obj, normalized_nodes[obj]["id"]["label"]))
        else:
            objects.append((obj, obj))
    subjects.sort(key=lambda x:x[1].upper())
    objects.sort(key=lambda x:x[1].upper())
    return (subjects, predicate_curies, objects)


def get_translated_options() -> (list, list):
    subject_subquery = s.query(models.Assertion.subject_curie.distinct())
    object_subquery = s.query(models.Assertion.object_curie.distinct())
    subject_curies = [sub[0] for sub in s.query(models.PRtoUniProt.uniprot.distinct()).filter(models.PRtoUniProt.pr.in_(subject_subquery))]
    object_curies = [obj[0] for obj in s.query(models.PRtoUniProt.uniprot.distinct()).filter(models.PRtoUniProt.pr.in_(object_subquery))]
    subject_curies.extend(sub[0] for sub in s.query(models.Assertion.subject_curie.distinct()).filter(models.Assertion.subject_curie.notilike('PR'), models.Assertion.subject_curie.notilike('UniProt')))
    subject_curies.extend(sub[0] for sub in s.query(models.Assertion.object_curie.distinct()).filter(models.Assertion.object_curie.notilike('PR'), models.Assertion.object_curie.notilike('UniProt')))
    list_to_normalize = []
    subjects = []
    objects = []
    list_to_normalize.extend(subject_curies)
    list_to_normalize.extend(object_curies)
    normalized_nodes = services.get_normalized_nodes(list_to_normalize)
    for subject in subject_curies:
        if subject in normalized_nodes and normalized_nodes[subject] is not None:
            subjects.append((subject, normalized_nodes[subject]["id"]["label"]))
        else:
            subjects.append((subject, subject))
    for obj in object_curies:
        if obj in normalized_nodes and normalized_nodes[obj] is not None:
            objects.append((obj, normalized_nodes[obj]["id"]["label"]))
        else:
            objects.append((obj, obj))
    subjects.sort(key=lambda x:x[1].upper())
    objects.sort(key=lambda x:x[1].upper())
    return (subjects, objects)


username = os.getenv('MYSQL_DATABASE_USER', None)
secret_password = os.getenv('MYSQL_DATABASE_PASSWORD', None)
EDGE_LIMIT = os.getenv('EDGE_LIMIT', 500)
assert username
assert secret_password
models.init_db(username=username, password=secret_password)
s = models.session()
(subjects, predicates, objects) = get_options()
(subjects_uniprot, objects_uniprot) = get_translated_options()


if __name__ == "__main__":
    print('main')
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

