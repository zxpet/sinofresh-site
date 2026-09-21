<?php
/**
 * Batch C — where does a declaration actually land?
 *
 * usage: php tools/b2d_c_php_scope.php <file.php> [name ...]
 *
 * Why this exists. The batch inserts two functions and one add_shortcode() call
 * into functions.php by anchoring on the seam between two top-level functions.
 * The first attempt anchored on the whole seam and spliced the block in FRONT of
 * it, which put every declaration inside sinofresh_formula_intro(). Nothing
 * noticed: `php -l` is happy, the splice's own undo proof is exact (it undoes a
 * clean splice), and the synthesiser models bytes rather than PHP scope. The
 * first real render did notice — on the 42 formula pages only, because those are
 * the pages that call intro(), and the second call fatal-failed with
 * "Cannot redeclare sinofresh_formula_faq_data()".
 *
 * So: a brace-depth check. A declaration is at include time exactly when it is
 * reached at depth 0 walking the file with the tokenizer. Depth is counted from
 * T_CURLY_OPEN / '{' / '}' plus the alternative-syntax pairs (T_IF/T_FOR/
 * T_FOREACH/T_WHILE/T_SWITCH followed by T_COLON), which is what a hand-rolled
 * brace counter otherwise gets wrong in a file this size.
 *
 * Exit status is 0 when every requested name is at depth 0, 1 otherwise.
 */

if ($argc < 2) {
    fwrite(STDERR, "usage: php b2d_c_php_scope.php <file.php> [name ...]\n");
    return 2;
}

$file  = $argv[1];
$want  = array_slice($argv, 2);
$src   = file_get_contents($file);
if ($src === false) {
    fwrite(STDERR, "cannot read $file\n");
    return 2;
}

$tokens = token_get_all($src);
$depth  = 0;
$pending_alt = false;   // a T_IF/T_FOR/... whose ':' alternative syntax we may see
$found  = array();      // name => array(line, depth)

for ($i = 0; $i < count($tokens); $i++) {
    $tok = $tokens[$i];

    if (is_array($tok)) {
        list($id, $text, $line) = $tok;

        if ($id === T_CURLY_OPEN || $id === T_DOLLAR_OPEN_CURLY_BRACES) {
            $depth++;
            continue;
        }
        if ($id === T_IF || $id === T_FOR || $id === T_FOREACH
            || $id === T_WHILE || $id === T_SWITCH) {
            $pending_alt = true;
            continue;
        }
        if ($id === T_FUNCTION) {
            // next non-whitespace, non-comment token that is a name
            for ($j = $i + 1; $j < count($tokens); $j++) {
                $n = $tokens[$j];
                if (is_array($n) && ($n[0] === T_WHITESPACE || $n[0] === T_COMMENT
                                     || $n[0] === T_DOC_COMMENT)) {
                    continue;
                }
                if (is_array($n) && $n[0] === T_STRING) {
                    if (!isset($found[$n[1]])) {
                        $found[$n[1]] = array($n[2], $depth);
                    }
                }
                break;
            }
            continue;
        }
        // anything that is neither whitespace nor comment ends the alt-syntax lookahead
        if ($pending_alt && $id !== T_WHITESPACE && $id !== T_COMMENT
            && $id !== T_DOC_COMMENT) {
            $pending_alt = false;
        }
        continue;
    }

    // single-character token
    if ($tok === '{') {
        $depth++;
        $pending_alt = false;
    } elseif ($tok === '}') {
        $depth--;
    } elseif ($tok === ':' && $pending_alt) {
        // `if (...):` / `foreach (...):` — this colon OPENS a block, closed by
        // endif;/endfor;/endforeach; (T_ENDIF and friends), which we treat as
        // a close below.
        $depth++;
        $pending_alt = false;
    }
}

// T_ENDIF/T_ENDFOR/T_ENDFOREACH/T_ENDWHILE/T_ENDSWITCH close an alternative block.
// Walk again, cheaply, only for those.
$alt_close = 0;
foreach ($tokens as $tok) {
    if (is_array($tok) && in_array($tok[0],
            array(T_ENDIF, T_ENDFOR, T_ENDFOREACH, T_ENDWHILE, T_ENDSWITCH), true)) {
        $alt_close++;
    }
}

$bad = 0;
if (!$want) {
    // no names asked for: report every declaration that is NOT at depth 0
    foreach ($found as $name => $info) {
        if ($info[1] !== 0) {
            printf("NESTED  %-44s line %-6d depth %d\n", $name, $info[0], $info[1]);
            $bad++;
        }
    }
    printf("%d declaration(s) found, %d nested, %d alternative-syntax close(s)\n",
           count($found), $bad, $alt_close);
} else {
    foreach ($want as $name) {
        if (!isset($found[$name])) {
            printf("MISSING %s\n", $name);
            $bad++;
            continue;
        }
        list($line, $d) = $found[$name];
        printf("%-8s %-44s line %-6d depth %d\n",
               $d === 0 ? 'TOPLEVEL' : 'NESTED', $name, $line, $d);
        if ($d !== 0) {
            $bad++;
        }
    }
}

return $bad === 0 ? 0 : 1;
