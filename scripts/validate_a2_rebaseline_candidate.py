"""Fail-closed source-locked A2 candidate audit; never operational acceptance.

Does not execute project CI suites or grant independent ADR ratification.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = 'governance/ABC_A2_SOURCE_BASELINE_CANDIDATE_20261110.json'
OLD = 'd8c7698bc060b859f5f4db52d572a00db656a2cd'
CURRENT = 'cfd57ecf29cd0b002270f4ac160fc0c6193a3c6b'
RUNS = [42208334348,42208334405,42208334526,42208334592,42208334762,42208334598]


class CandidateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CandidateError(message)


def validate(data, *, root=None, check_files=False):
    require(data.get('schema') == 'abc.a2.rebaseline.review-candidate.v1', 'schema')
    require(data.get('status') == 'CANDIDATE_SOURCE_LOCKED_NOT_VALIDATED', 'candidate_status')
    require(data.get('admissible_as_operational_baseline') is False, 'not_operational')
    require(data.get('candidate_code_commit_sha') == CURRENT, 'candidate_code_sha')
    require(data.get('candidate_stack') == {
        'a2_packet_pr':78, 'a2_packet_sha':'026e1fb174919278e3c2d73442be10b4f11675a4',
        'adr005_ttl_pr':88, 'adr005_ttl_sha':'f99109dfd4d2147287bdf704beeb93d202a88e41',
        'spiffe_boundary_pr':89
    }, 'stacked_pr_lineage')
    previous=data.get('prior_approved_ci_source',{})
    require(previous.get('code_sha') == OLD and OLD != CURRENT, 'old_ci_only')
    require(previous.get('success_run_ids') == RUNS, 'historical_runs')
    require(previous.get('historical_mapped_jobs') == 55, 'historic_test_coverage')
    require(previous.get('coverage_class') == 'HISTORICAL_SYNTHETIC_TEST_EVIDENCE_NOT_VALID_FOR_CANDIDATE', 'no_ci_promotion')
    evid=data.get('current_evidence',{})
    require(evid.get('operational_gate_count') == 80 and evid.get('operational_gate_status') == 'OPEN', 'gate_states')
    require(evid.get('historical_test_mapped_count') == 55 and evid.get('unmapped_direct_test_count') == 25, 'mapping_counts')
    require(evid.get('open_risk_count') == 14 and evid.get('signatures_count') == 0, 'risk_signature_counts')
    for key in ('full_checkout_repo_tests','new_jwt_eng14_native_tests','postgresql16_suite','ci_at_candidate_sha'):
        require(evid.get(key) == 'NOT_RUN', 'false_test_pass:'+key)
    for name, expected in (('local_isolated_repo_tests',7),('local_non_repository_probes',15)):
        item=evid.get(name,{})
        require(item.get('executed') == expected and item.get('passed') == expected, 'local_test_count:'+name)
    approval=data.get('approvals',{})
    for key in ('architecture','security','sre','professional'):
        require(approval.get(key) == 'NOT_RECEIVED', 'unverified_signoff:'+key)
    require(approval.get('owner_staging_cost') == 'NOT_AUTHORIZED', 'owner_cost_hold')
    design=data.get('design_recommendation',{})
    require(design.get('status') == 'RECOMMEND_APPROVE_DESIGN_ONLY_WITH_CONDITIONS_NOT_RATIFIED','adr_not_ratified')
    require(design.get('reviewer_id') is None and design.get('reviewer_signature') is None,'fake_reviewer')
    require(design.get('reviewed_commit') == CURRENT,'adr_source_sha')
    for key,val in data.get('release_policy',{}).items():
        require(val is False,'unauthorized_release:'+key)
    require(len(data.get('release_policy',{})) == 7,'release_policy_complete')
    tree=data.get('source_tree',{})
    require(tree.get('truncated') is False and tree.get('blobs',0) >= 600,'source_tree')
    blobs=data.get('locked_git_blob_shas',{})
    require(len(blobs)==15,'locked_file_count')
    for path,blob in blobs.items():
        require(isinstance(path,str) and path and not path.startswith('/') and '..' not in Path(path).parts,'unsafe_file_path')
        require(re.fullmatch(r'[0-9a-f]{40}',blob or '') is not None,'invalid_blob_sha')
        if check_files:
            require(root is not None,'full_checkout_required')
            source=(root/path).resolve()
            require(source.is_relative_to(root.resolve()) and source.is_file(),'source_file_missing:'+path)
            data_bytes=source.read_bytes()
            actual=hashlib.sha1(b'blob '+str(len(data_bytes)).encode()+b'\x00'+data_bytes).hexdigest()
            require(actual==blob,'blob_provenance_mismatch:'+path)
    if check_files:
        matrix=json.loads((root/'governance/ABC_A2_G01_G10_EVIDENCE_RECONCILIATION_v1.json').read_text())
        risks=json.loads((root/'governance/ABC_A2_INDEPENDENT_RISK_REGISTER_v1.json').read_text())
        require(matrix.get('baseline_code_sha') == OLD and risks.get('base_code_sha') == OLD,'historical_ledger_unexpectedly_promoted')
        gates=[g for s in matrix.get('scopes',[]) for g in s.get('gates',[])]
        require(len(gates)==80 and all(g.get('operational_status')=='OPEN' for g in gates),'operational_gates')
        require(sum(bool(g.get('covered_by_tests')) for g in gates)==55,'historic_mapped_gates')
        require(len(risks.get('risks',[]))==14 and all(r.get('status')=='OPEN' for r in risks['risks']),'open_risk_records')
    return {'status':'PASS_SOURCE_CANDIDATE_ONLY_NOT_CI_NOT_APPROVAL',
            'locked_paths':len(blobs), 'historic_ci_source':OLD,
            'current_source':CURRENT, 'full_file_hashes_checked':check_files}


def self_test(value):
    baseline=validate(value)
    mutations=[
        ('fake_ci_run',lambda o:o['current_evidence'].__setitem__('ci_at_candidate_sha','PASS')),
        ('fake_full_checkout',lambda o:o['current_evidence'].__setitem__('full_checkout_repo_tests','PASS')),
        ('fake_native_jwt',lambda o:o['current_evidence'].__setitem__('new_jwt_eng14_native_tests','PASS')),
        ('fake_pg',lambda o:o['current_evidence'].__setitem__('postgresql16_suite','PASS')),
        ('fake_arch',lambda o:o['approvals'].__setitem__('architecture','APPROVED')),
        ('fake_security',lambda o:o['approvals'].__setitem__('security','APPROVED')),
        ('fake_signer',lambda o:o['design_recommendation'].__setitem__('reviewer_id','fake')),
        ('fake_operational',lambda o:o.__setitem__('admissible_as_operational_baseline',True)),
        ('fake_eng06',lambda o:o['release_policy'].__setitem__('eng06_customer_release',True)),
        ('fake_cost',lambda o:o['approvals'].__setitem__('owner_staging_cost','APPROVED')),
        ('fake_ci_sha',lambda o:o['prior_approved_ci_source'].__setitem__('code_sha',CURRENT)),
        ('missing_blob',lambda o:o['locked_git_blob_shas'].pop(next(iter(o['locked_git_blob_shas']))))
    ]
    rejected=0
    for name,mutate in mutations:
        specimen=copy.deepcopy(value)
        mutate(specimen)
        try:validate(specimen)
        except CandidateError:rejected+=1
        else:raise CandidateError('negative_test_not_rejected:'+name)
    return {'baseline':baseline,'negative_mutations_rejected':rejected,
            'negative_mutations_total':len(mutations)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--metadata-only',action='store_true',help='No repo checkout or original suite execution')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--require-operational',action='store_true')
    args=parser.parse_args()
    packet=json.loads((ROOT/PACKET).read_text())
    result=self_test(packet) if args.self_test else validate(packet,root=ROOT,check_files=not args.metadata_only)
    if args.require_operational:
        raise CandidateError('OPERATIONAL_A2_CLOSURE_BLOCKED_CI_AND_INDEPENDENT_SIGNOFF_MISSING')
    print(json.dumps(result,sort_keys=True,indent=2))


if __name__=='__main__':
    main()
