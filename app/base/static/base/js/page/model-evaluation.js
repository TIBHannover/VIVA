function setEvalSortMode(evalSortMode) {
    Cookies.set('eval_sort_mode', evalSortMode, {expires: 365, sameSite: 'Lax'});
    location.reload();
}