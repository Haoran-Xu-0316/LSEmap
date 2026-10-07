"""Finite CON exterior audit after correcting a source attribution mismatch."""


def apply_con_exterior175():
    """Return an explicit no-op; never invent CON geometry from CLM photographs."""
    return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[],
                changedObjects=[], auditOnly=True,
                reason='No new photograph-supported regional CON correction established',
                evidenceCorrection='2018-04-24 and2023-11-15 facade photos belong to CLM, not CON',
                photographCaptureDate='Official CON entrance crop date unknown',
                limitations=['Entire upper rows, side elevation and roof remain inherited estimates',
                             'Tower round4 CON photos cover renovated internal Methodology rooms',
                             'Official entrance crop supports existing granite/limestone split and compact four-light portal window',
                             'One focused official search returned no registered full-height CON exterior'])
