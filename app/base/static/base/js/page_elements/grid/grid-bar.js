function setupGridBarDimensions(grid, barTemplate) {
    barTemplate.find('.grid-bar-col-count').each(function () {
        $(this).text(grid.cols);
    });
    barTemplate.find('.grid-bar-row-count').each(function () {
        $(this).text(grid.rows);
    });
    barTemplate.find('.grid-bar-dimensions-cols').each(function () {
        $(this).on('click', function () {
            let that = this;
            grid.proposeUpdate(function () {
                let newCols = $(that).data('value');
                grid.page = Math.ceil((this.cols * this.rows * (grid.page - 1) + 1) / (newCols * this.rows));
                grid.cols = newCols;
                Cookies.set('grid_cols', newCols, {expires: 365, sameSite: 'Lax'});
            });
        });
    });
    barTemplate.find('.grid-bar-dimensions-rows').each(function () {
        $(this).on('click', function () {
            let that = this;
            grid.proposeUpdate(function () {
                let newRows = $(that).data('value');
                grid.page = Math.ceil((this.cols * this.rows * (grid.page - 1) + 1) / (this.cols * newRows));
                grid.rows = newRows;
                Cookies.set('grid_rows', newRows, {expires: 365, sameSite: 'Lax'});
            });
        });
    });
    return barTemplate;
}

function setupGridBarPagination(grid, barTemplate) {
    let maxPageNum = Math.ceil(grid.elementCount / (grid.rows * grid.cols));

    if (grid.page === 1) {
        barTemplate.find('.grid-bar-pagination-before').each(function () {
            $(this).addClass('disabled');
        });
    } else {
        if (grid.page < 6) {
            barTemplate.find('.grid-bar-pagination-5previous').addClass('disabled');
        } else {
            barTemplate.find('.grid-bar-pagination-5previous').find('.page-link').on('click', function () {
                grid.proposeUpdate(function () {
                    grid.page -= 5;
                });
            });
        }
        barTemplate.find('.grid-bar-pagination-first').find('.page-link').on('click', function () {
            grid.proposeUpdate(function () {
                grid.page = 1;
            });
        });
        barTemplate.find('.grid-bar-pagination-previous').find('.page-link').on('click', function () {
            grid.proposeUpdate(function () {
                grid.page -= 1;
            });
        });
    }

    let inputsPaginationPage = barTemplate.find('.grid-bar-pagination-current');
    inputsPaginationPage[0].value = grid.page;
    inputsPaginationPage.attr('size', Math.floor(Math.log10(maxPageNum)) + 1);
    inputsPaginationPage.on('keyup', function () {
        if (!grid.timeoutPagination) {
            clearTimeout(grid.timeoutPagination);
        }
        grid.timeoutPagination = setTimeout(function () {
            let newPage = inputsPaginationPage[0].value;
            if (isNaN(newPage) || parseInt(newPage) < 1 || parseInt(newPage) > maxPageNum) {
                inputsPaginationPage[0].value = grid.page;
            } else {
                // this timeout will be called again after resetting value if value invalid
                if (grid.page !== parseInt(newPage)) {
                    grid.proposeUpdate(function () {
                        grid.page = parseInt(newPage);
                        inputsPaginationPage[0].value = grid.page;
                    });
                }
            }
        }, 1200);
    });
    barTemplate.find('.grid-bar-pagination-max').text(maxPageNum);

    if (grid.page === maxPageNum) {
        barTemplate.find('.grid-bar-pagination-after').each(function () {
            $(this).addClass('disabled');
        })
    } else {
        if (grid.page > maxPageNum - 5) {
            barTemplate.find('.grid-bar-pagination-5next').addClass('disabled');
        } else {
            barTemplate.find('.grid-bar-pagination-5next').find('.page-link').on('click', function () {
                grid.proposeUpdate(function () {
                    grid.page += 5;
                });
            });
        }
        barTemplate.find('.grid-bar-pagination-next').find('.page-link').on('click', function () {
            grid.proposeUpdate(function () {
                grid.page += 1;
            });
        });
        barTemplate.find('.grid-bar-pagination-last').find('.page-link').on('click', function () {
            grid.proposeUpdate(function () {
                grid.page = Math.ceil(grid.elementCount / (grid.rows * grid.cols));
            });
        });
    }

    return barTemplate;
}

function setupGridBarAnnotation(grid, barTemplate) {
    let gridAnnotation = barTemplate.find('.grid-bar-annotation');
    gridAnnotation.find('.grid-bar-annotation-save').on('click', function () {
        grid.saveAnnotations();
    });
    gridAnnotation.find('.grid-bar-annotation-positive').on('click', function () {
        grid.changeGridAnnotations(Annotation.POSITIVE);
    });
    gridAnnotation.find('.grid-bar-annotation-negative').on('click', function () {
        grid.changeGridAnnotations(Annotation.NEGATIVE);
    });
    gridAnnotation.find('.grid-bar-annotation-neutral').on('click', function () {
        grid.changeGridAnnotations(Annotation.NEUTRAL);
    });
    return barTemplate;
}

function setupGridBarFace(grid, barTemplate) {
    let gridFace = barTemplate.find('.grid-bar-face');
    barTemplate.find('.grid-bar-face-value').each(function () {
        $(this).text(grid.face.charAt(0).toUpperCase() + grid.face.slice(1));
    });
    barTemplate.find('.grid-bar-face-value-default').each(function () {
        $(this).on('click', function () {
            let that = this;
            grid.proposeUpdate(function () {
                let new_face_value = $(that)[0].getAttribute("data-value")
                grid.face = new_face_value
                Cookies.set('face', new_face_value, {expires: 365, sameSite: 'Lax'});
            });
        });
    });
    barTemplate.find('.grid-bar-face-value-photo').each(function () {
        $(this).on('click', function () {
            let that = this;
            grid.proposeUpdate(function () {
                let new_face_value = $(that)[0].getAttribute("data-value")
                grid.face = new_face_value
                Cookies.set('face', new_face_value, {expires: 365, sameSite: 'Lax'});
            });
        });
    });
    barTemplate.find('.grid-bar-face-value-face').each(function () {
        $(this).on('click', function () {
            let that = this;
            grid.proposeUpdate(function () {
                let new_face_value = $(that)[0].getAttribute("data-value")
                grid.face = new_face_value
                Cookies.set('face', new_face_value, {expires: 365, sameSite: 'Lax'});
            });
        });
    });
    return barTemplate;
}
