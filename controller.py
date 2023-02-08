from flask import Flask, render_template, request
from sqlalchemy import select, text, insert
import os
import models
import services
import json

app = Flask(__name__)


# Start with a hard-coded list of predicates to avoid having to query the evidence_score table for the list.
predicates = ['biolink:entity_negatively_regulates_entity', 'biolink:entity_positively_regulates_entity',
              'biolink:gain_of_function_contributes_to', 'biolink:loss_of_function_contributes_to', 'biolink:treats',
              'biolink:contributes_to', 'false']


@app.route('/')
def index():
    return render_template("freetext_search.html", predicates=predicates)


@app.route('/public/', strict_slashes=False)
def public_index():
    (subjects, objects) = get_options()
    return render_template("mockup.html", subjects=subjects, predicates=predicates, objects=objects)


@app.route('/translator/', strict_slashes=False)
def translator_index():
    (subjects_uniprot, objects_uniprot) = get_translated_options()
    return render_template("mockup.html", subjects=subjects_uniprot, predicates=predicates, objects=objects_uniprot)


@app.route('/assertion/<aid>', strict_slashes=False)
@app.route('/assertions/<aid>', strict_slashes=False)
def assertion_lookup(aid):
    assertion_query_by_id = s.query(models.Assertion).filter(models.Assertion.assertion_id == aid)
    if assertion_query_by_id.count() == 0:
        return "No results found"
    return render_template("assertion.html", title="Assertion Display", assertion=assertion_query_by_id.one())


@app.route('/evidence/<evidence_id>', strict_slashes=False)
def evidence_lookup(evidence_id):
    evidence_query_by_id = s.query(models.Evidence).filter(models.Evidence.evidence_id == evidence_id)
    if evidence_query_by_id.count() == 0:
        return "No results found"
    return render_template("evidence.html", title="Evidence Display", evidence=evidence_query_by_id.one())


@app.route('/query/', methods=['POST'], strict_slashes=False)
def assertion_query():
    if request.is_json:
        request_dict = json.loads(request.data)
        subject_curie = request_dict['subject']
        predicate_curie = request_dict['predicate']
        object_curie = request_dict['object']
        if subject_curie.lower() == 'any':
            if object_curie.lower() == 'any':
                assertion_list = s.query(models.Assertion).limit(EDGE_LIMIT)
            else:
                if object_curie.startswith('UniProtKB'):
                    assertion_list = s.query(models.Assertion)\
                        .where(models.Assertion.object_uniprot.has(models.PRtoUniProt.uniprot == object_curie))\
                        .limit(EDGE_LIMIT)
                else:
                    assertion_list = s.query(models.Assertion)\
                        .where(models.Assertion.object_curie == object_curie)\
                        .limit(EDGE_LIMIT)
        else:
            if object_curie == 'Any':
                if subject_curie.startswith('UniProtKB'):
                    assertion_list = s.query(models.Assertion)\
                        .where(models.Assertion.subject_uniprot.has(models.PRtoUniProt.uniprot == subject_curie))\
                        .limit(EDGE_LIMIT)
                else:
                    assertion_list = s.query(models.Assertion)\
                        .where(models.Assertion.subject_curie == subject_curie)\
                        .limit(EDGE_LIMIT)
            else:
                if object_curie.startswith('UniProtKB'):
                    if subject_curie.startswith('UniProtKB'):
                        assertion_list = s.query(models.Assertion)\
                            .where(models.Assertion.object_uniprot.has(models.PRtoUniProt.uniprot == object_curie),
                                   models.Assertion.subject_uniprot.has(models.PRtoUniProt.uniprot == subject_curie))\
                            .limit(EDGE_LIMIT)
                    else:
                        assertion_list = s.query(models.Assertion)\
                            .where(models.Assertion.object_uniprot.has(models.PRtoUniProt.uniprot == object_curie),
                                   models.Assertion.subject_curie == subject_curie)\
                            .limit(EDGE_LIMIT)
                else:
                    if subject_curie.startswith('UniProtKB'):
                        assertion_list = s.query(models.Assertion)\
                            .where(models.Assertion.object_curie == object_curie,
                                   models.Assertion.subject_uniprot.has(models.PRtoUniProt.uniprot == subject_curie))\
                            .limit(EDGE_LIMIT)
                    else:
                        assertion_list = s.query(models.Assertion)\
                            .where(models.Assertion.subject_curie == subject_curie,
                                   models.Assertion.object_curie == object_curie)\
                            .limit(EDGE_LIMIT)
        edges = []
        for edge in get_edge_list(assertion_list, use_uniprot=(subject_curie.startswith('UniProtKB') or
                                                               object_curie.startswith('UniProtKB'))):
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
            "results": edges
        }
        return json.dumps(results), 200
    return 'something else', 400


@app.route('/evaluations/', methods=['POST'], strict_slashes=False)
def add_evaluation():
    if not request.is_json:
        return 'nope', 400
    request_dict = json.loads(request.data)
    insert_statement = insert(models.Evaluation).values(
        evidence_id=request_dict['evidence_id'],
        overall_correct=request_dict['overall_correct'],
        subject_correct=request_dict['subject_correct'],
        object_correct=request_dict['object_correct'],
        predicate_correct=request_dict['predicate_correct'],
        comments=request_dict['comments'] if 'comments' in request_dict else None,
        source_id=TMUI_ID
    )
    s.execute(insert_statement)
    s.commit()
    return {}, 201


@app.route('/api/curies/subject/', strict_slashes=False)
def get_available_subject_curies():
    query = select(text('DISTINCT subject_curie FROM assertion'))
    results = [curie for curie, in s.execute(query)]
    print(f"Subject count: {len(results)}")
    return json.dumps(results)


@app.route('/api/curies/object/', strict_slashes=False)
def get_available_object_curies():
    query = select(text('DISTINCT object_curie FROM assertion'))
    results = [curie for curie, in s.execute(query)]
    print(f"Object count: {len(results)}")
    return json.dumps(results)


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
        # these are the predicates that have the high score for at least one evidence
        predicate_list = assertion.get_predicates()
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
                        "subject_span": ev.subject_entity.span if ev.subject_entity else "0|0",
                        "object_span": ev.object_entity.span if ev.object_entity else "0|0",
                        "subject_curie": sub,
                        "object_curie": obj
                    })
    return edge_list


def get_predicates() -> list:
    return [predicate for predicate, in s.execute(select(text('DISTINCT predicate_curie FROM evidence_score')))]


def get_options() -> (list, list):
    subject_curies = [sub[0] for sub in s.query(models.Assertion.subject_curie).distinct()]
    object_curies = [obj[0] for obj in s.query(models.Assertion.object_curie).distinct()]
    list_to_normalize = []
    subjects = []
    objects = []
    list_to_normalize.extend(subject_curies)
    list_to_normalize.extend(object_curies)
    normalized_nodes = services.get_normalized_nodes(list_to_normalize)
    for subject in subject_curies:
        if subject in normalized_nodes and normalized_nodes[subject] is not None:
            subjects.append((
                subject,
                normalized_nodes[subject]['id']['label'] if 'label' in normalized_nodes[subject]['id'] else subject))
        else:
            subjects.append((subject, subject))
    for obj in object_curies:
        if obj in normalized_nodes and normalized_nodes[obj] is not None:
            objects.append((
                obj,
                normalized_nodes[obj]['id']['label'] if 'label' in normalized_nodes[obj]['id'] else obj))
        else:
            objects.append((obj, obj))
    subjects.sort(key=lambda x: x[1].upper())
    objects.sort(key=lambda x: x[1].upper())
    return subjects, objects


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
            subjects.append((subject, normalized_nodes[subject]['id']['label'] if 'label' in normalized_nodes[subject]['id'] else subject))
        else:
            subjects.append((subject, subject))
    for obj in object_curies:
        if obj in normalized_nodes and normalized_nodes[obj] is not None:
            objects.append((obj, normalized_nodes[obj]['id']['label'] if 'label' in normalized_nodes[obj]['id'] else obj))
        else:
            objects.append((obj, obj))
    subjects.sort(key=lambda x: x[1].upper())
    objects.sort(key=lambda x: x[1].upper())
    return subjects, objects


username = os.getenv('MYSQL_DATABASE_USER', None)
secret_password = os.getenv('MYSQL_DATABASE_PASSWORD', None)
EDGE_LIMIT = int(os.getenv('EDGE_LIMIT', '500'))
TMUI_ID = 0
assert username
assert secret_password
models.init_db(username=username, password=secret_password)
s = models.session()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

