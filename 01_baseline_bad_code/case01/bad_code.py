def f(a,b,c):
    r=0
    if a>10:
        if b>5:
            r=a+b+c
        else:
            r=a-b+c
    else:
        if c>0:
            r=a+b-c
        else:
            r=a-b-c
    for i in range(0,10):
        if i%2==0:
            r=r+i
        else:
            r=r-i
    return r
